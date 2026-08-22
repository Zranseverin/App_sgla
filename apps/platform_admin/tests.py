from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.entreprises.models import Entreprise
from apps.plan.models import Plan
from apps.platform_admin.models import CleanGoAdmin
from apps.platform_admin.models import CleanGoMailConfiguration
from apps.platform_admin.services import send_expiration_reminder


class PlatformAdminTests(TestCase):
    def setUp(self):
        self.plan = Plan.objects.create(
            code="PRO",
            nom="Professionnel",
            prix_mensuel=15000,
            devise="XOF",
            duree_essai_jours=8,
            actif=True,
        )
        self.admin = CleanGoAdmin.objects.create(
            nom="Admin CleanGo",
            email="admin@cleango.test",
            password="unused",
            statut="actif",
        )
        self.mail_configuration = CleanGoMailConfiguration.objects.create(
            nom_expediteur="CleanGo",
            email_expediteur="noreply@cleango.test",
            serveur_smtp="smtp.cleango.test",
            port_smtp=465,
            utilisateur_smtp="noreply@cleango.test",
            actif=True,
        )
        self.mail_configuration.set_password("smtp-secret")
        self.mail_configuration.save()
        session = self.client.session
        session["platform_admin_id"] = self.admin.pk
        session.save()

    def test_dashboard_is_available_to_platform_admin(self):
        response = self.client.get(reverse("platform_admin:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Administration CleanGo")

    def test_dedicated_admin_login(self):
        self.admin.set_password("Admin-Secret-123")
        self.admin.save(update_fields=["password"])
        self.client.session.flush()
        response = self.client.post(reverse("platform_admin:login"), {
            "email": self.admin.email,
            "password": "Admin-Secret-123",
        })
        self.assertRedirects(response, reverse("platform_admin:dashboard"))

    def test_dashboard_redirects_to_dedicated_login(self):
        self.client.session.flush()
        response = self.client.get(reverse("platform_admin:dashboard"))
        self.assertRedirects(
            response,
            reverse("platform_admin:login"),
            fetch_redirect_response=False,
        )

    def test_admin_can_create_and_disable_plan(self):
        response = self.client.post(reverse("platform_admin:plan_create"), {
            "code": "PREMIUM",
            "nom": "Premium",
            "description": "Offre complète",
            "prix_mensuel": "30000",
            "devise": "XOF",
            "duree_essai_jours": "8",
            "max_centres": "5",
            "max_utilisateurs": "20",
            "quota_sms_mensuel": "500",
            "actif": "on",
        })
        self.assertRedirects(response, reverse("platform_admin:plan_list"))
        plan = Plan.objects.get(code="PREMIUM")
        self.assertTrue(plan.actif)

        response = self.client.post(
            reverse("platform_admin:plan_toggle", args=[plan.pk]),
        )
        self.assertRedirects(response, reverse("platform_admin:plan_list"))
        plan.refresh_from_db()
        self.assertFalse(plan.actif)

    def test_admin_can_save_platform_mail_configuration(self):
        response = self.client.post(reverse("platform_admin:mail_configuration"), {
            "nom_expediteur": "CleanGo",
            "email_expediteur": "noreply@cleango.test",
            "serveur_smtp": "smtp.cleango.test",
            "port_smtp": "465",
            "utilisateur_smtp": "noreply@cleango.test",
            "mot_de_passe": "smtp-secret",
            "utiliser_ssl": "on",
            "actif": "on",
        })
        self.assertRedirects(response, reverse("platform_admin:mail_configuration"))
        configuration = CleanGoMailConfiguration.objects.get()
        self.assertNotEqual(configuration.mot_de_passe_chiffre, "smtp-secret")
        self.assertEqual(configuration.get_password(), "smtp-secret")

    def test_expiration_reminder_is_sent_only_once(self):
        from datetime import timedelta
        from django.utils import timezone

        company = Entreprise.objects.create(
            raison_sociale="Essai bientôt terminé",
            email_contact="client@cleango.test",
            plan=self.plan,
            statut_abonnement="essai",
            date_debut_essai=timezone.localdate(),
            date_fin_essai=timezone.localdate() + timedelta(days=3),
            devise="XOF",
            langue="fr",
            fuseau_horaire="Africa/Abidjan",
        )
        with patch("apps.platform_admin.services.EmailMultiAlternatives.send", return_value=1) as sender:
            first = send_expiration_reminder(company, company.date_fin_essai, "https://cleango.test/")
            second = send_expiration_reminder(company, company.date_fin_essai, "https://cleango.test/")
        self.assertTrue(first)
        self.assertFalse(second)
        sender.assert_called_once()

    def test_admin_can_create_enterprise_and_activate_subscription(self):
        with patch("apps.platform_admin.views._send_enterprise_credentials") as send_credentials:
            response = self.client.post(reverse("platform_admin:create_enterprise"), {
                "raison_sociale": "Lavage Ivoire",
                "email_contact": "contact@lavage.test",
                "telephone_contact": "0102030405",
                "adresse": "Abidjan",
                "plan": self.plan.pk,
                "statut_abonnement": "essai",
                "duree_mois": "1",
                "admin_nom": "Responsable Lavage",
                "admin_email": "responsable@lavage.test",
                "admin_telephone": "0506070809",
            })
        send_credentials.assert_called_once()
        company = Entreprise.objects.get(email_contact="contact@lavage.test")
        self.assertRedirects(
            response,
            reverse("platform_admin:enterprise_detail", args=[company.pk]),
        )
        self.assertEqual(company.statut_abonnement, "essai")
        self.assertTrue(company.utilisateurs.filter(role__code="admin").exists())

        with patch("apps.platform_admin.views.send_payment_confirmation") as confirmation:
            response = self.client.post(
                reverse("platform_admin:activate_subscription", args=[company.pk]),
                {"plan": self.plan.pk, "duree_mois": "3"},
            )
        confirmation.assert_called_once()
        self.assertRedirects(
            response,
            reverse("platform_admin:enterprise_detail", args=[company.pk]),
        )
        company.refresh_from_db()
        self.assertEqual(company.statut_abonnement, "actif")
        self.assertIsNotNone(company.date_fin_abonnement)
        self.assertEqual(company.paiements_abonnement.filter(statut="paye").count(), 1)
