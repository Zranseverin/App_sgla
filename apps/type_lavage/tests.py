from django.test import TestCase
from django.urls import reverse

from apps.authentication.models import User
from apps.entreprises.models import Entreprise
from apps.plan.models import Plan
from apps.roles.models import Role

from .models import TypeLavage


class TypeLavageTests(TestCase):
    def setUp(self):
        plan = Plan.objects.create(
            code="wash-test",
            nom="Test",
            prix_mensuel="0",
            devise="XOF",
            duree_essai_jours=14,
            actif=True,
        )
        self.entreprise = Entreprise.objects.create(
            raison_sociale="Lavage Test",
            devise="XOF",
            langue="fr",
            fuseau_horaire="Africa/Abidjan",
            statut_abonnement="essai",
            email_contact="lavage@example.com",
            plan=plan,
        )
        role = Role.objects.create(
            entreprise=self.entreprise,
            code="admin",
            libelle="Administrateur",
        )
        self.user = User(
            nom="Admin Lavage",
            email="admin.lavage@example.com",
            statut="actif",
            entreprise=self.entreprise,
            role=role,
        )
        self.user.set_password("TestPassword123!")
        self.user.save()
        session = self.client.session
        session["utilisateur_id"] = self.user.pk
        session.save()

    def test_create_list_update_and_soft_delete(self):
        response = self.client.post(reverse("type_lavage:create"), {
            "libelle": "Lavage complet",
            "description": "Lavage intérieur et extérieur",
            "prix_unitaire": "10000",
            "duree_estimee_min": "45",
            "actif": "on",
        })
        self.assertRedirects(response, reverse("type_lavage:index"))
        item = TypeLavage.objects.get()
        self.assertEqual(item.entreprise, self.entreprise)
        self.assertEqual(item.user, self.user)
        self.assertEqual(item.created_by, self.user)

        response = self.client.get(reverse("type_lavage:index"))
        self.assertContains(response, "Lavage complet")

        response = self.client.post(reverse("type_lavage:update", args=[item.pk]), {
            "libelle": "Lavage premium",
            "description": "Service premium",
            "prix_unitaire": "15000",
            "duree_estimee_min": "60",
            "actif": "on",
        })
        self.assertRedirects(response, reverse("type_lavage:index"))
        item.refresh_from_db()
        self.assertEqual(item.libelle, "Lavage premium")
        self.assertEqual(item.updated_by, self.user)

        response = self.client.post(reverse("type_lavage:delete", args=[item.pk]))
        self.assertRedirects(response, reverse("type_lavage:index"))
        item.refresh_from_db()
        self.assertIsNotNone(item.deleted_at)
        self.assertEqual(item.deleted_by, self.user)
        self.assertFalse(item.actif)
