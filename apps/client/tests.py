from django.test import TestCase
from django.urls import reverse

from apps.authentication.models import User
from apps.entreprises.models import Entreprise
from apps.plan.models import Plan
from apps.roles.models import Role

from .models import Client


class ClientTests(TestCase):
    def setUp(self):
        plan = Plan.objects.create(
            code="client-test",
            nom="Test",
            prix_mensuel="0",
            devise="XOF",
            duree_essai_jours=14,
            actif=True,
        )
        self.entreprise = Entreprise.objects.create(
            raison_sociale="Entreprise Clients",
            devise="XOF",
            langue="fr",
            fuseau_horaire="Africa/Abidjan",
            statut_abonnement="essai",
            email_contact="clients@example.com",
            plan=plan,
        )
        role = Role.objects.create(
            entreprise=self.entreprise,
            code="admin",
            libelle="Administrateur",
        )
        self.user = User(
            nom="Admin Clients",
            email="admin.clients@example.com",
            statut="actif",
            entreprise=self.entreprise,
            role=role,
        )
        self.user.set_password("TestPassword123!")
        self.user.save()
        session = self.client.session
        session["utilisateur_id"] = self.user.pk
        session.save()

    def test_client_crud_and_generated_code(self):
        response = self.client.post(reverse("client:create"), {
            "nom_complet": "Jean Kouassi",
            "adresse": "Cocody, Abidjan",
            "telephone": "+2250700000000",
            "email": "jean@example.com",
        })
        self.assertRedirects(response, reverse("client:index"))
        client = Client.objects.get()
        self.assertRegex(client.code, r"^CLI-[A-F0-9]{6}$")
        self.assertEqual(client.entreprise, self.entreprise)
        self.assertEqual(client.created_by, self.user)

        response = self.client.get(reverse("client:index"), {"q": "Jean"})
        self.assertContains(response, "Jean Kouassi")

        response = self.client.post(reverse("client:update", args=[client.pk]), {
            "nom_complet": "Jean Kouassi Modifié",
            "adresse": "Riviera, Abidjan",
            "telephone": "+2250700000000",
            "email": "jean@example.com",
        })
        self.assertRedirects(response, reverse("client:index"))
        client.refresh_from_db()
        self.assertEqual(client.nom_complet, "Jean Kouassi Modifié")
        self.assertEqual(client.updated_by, self.user)

        response = self.client.post(reverse("client:delete", args=[client.pk]))
        self.assertRedirects(response, reverse("client:index"))
        client.refresh_from_db()
        self.assertIsNotNone(client.deleted_at)
        self.assertEqual(client.deleted_by, self.user)
