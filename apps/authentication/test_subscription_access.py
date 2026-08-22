from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.entreprises.models import Entreprise
from apps.plan.models import Plan
from apps.roles.models import Role

from .models import User


class SubscriptionAccessMiddlewareTests(TestCase):
    def setUp(self):
        self.plan = Plan.objects.create(
            code="access-test",
            nom="Test accès",
            description="",
            prix_mensuel="1000.00",
            devise="XOF",
            max_centres=1,
            max_utilisateurs=5,
            quota_sms_mensuel=0,
            duree_essai_jours=14,
            actif=True,
        )
        self.entreprise = Entreprise.objects.create(
            raison_sociale="Entreprise test",
            devise="XOF",
            langue="fr",
            fuseau_horaire="Africa/Abidjan",
            statut_abonnement="essai",
            date_debut_essai=timezone.localdate() - timedelta(days=15),
            date_fin_essai=timezone.localdate() - timedelta(days=1),
            email_contact="contact@example.com",
            plan=self.plan,
        )
        self.role = Role.objects.create(
            entreprise=self.entreprise, code="admin", libelle="Administrateur"
        )
        self.user = User.objects.create(
            nom="Admin Test",
            email="admin@example.com",
            password="unused",
            statut="actif",
            entreprise=self.entreprise,
            role=self.role,
        )
        session = self.client.session
        session["utilisateur_id"] = self.user.pk
        session.save()

    def test_expired_trial_is_redirected_from_business_page(self):
        response = self.client.get(reverse("dashboard:index"))

        self.assertRedirects(
            response,
            reverse("authentication:subscription_expired"),
            fetch_redirect_response=False,
        )

    def test_expiration_page_and_logout_remain_accessible(self):
        response = self.client.get(reverse("authentication:subscription_expired"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Votre accès a expiré")

    def test_trial_is_valid_through_its_end_date(self):
        self.entreprise.date_fin_essai = timezone.localdate()
        self.entreprise.save(update_fields=["date_fin_essai"])

        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 200)

    def test_expired_paid_subscription_is_blocked(self):
        self.entreprise.statut_abonnement = "actif"
        self.entreprise.date_fin_abonnement = timezone.localdate() - timedelta(days=1)
        self.entreprise.save(update_fields=["statut_abonnement", "date_fin_abonnement"])

        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("authentication:subscription_expired"))

    def test_only_subscription_configuration_remains_accessible(self):
        configuration = reverse("authentication:configuration")

        blocked = self.client.get(f"{configuration}?tab=accounts")
        renewal = self.client.get(f"{configuration}?tab=subscription")

        self.assertEqual(blocked.status_code, 302)
        self.assertEqual(blocked.url, reverse("authentication:subscription_expired"))
        self.assertEqual(renewal.status_code, 200)
