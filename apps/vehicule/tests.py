from django.test import TestCase
from django.urls import reverse

from apps.authentication.models import User
from apps.client.models import Client
from apps.entreprises.models import Entreprise
from apps.plan.models import Plan
from apps.roles.models import Role

from .models import Vehicule


class VehiculeTests(TestCase):
    def setUp(self):
        plan = Plan.objects.create(
            code="vehicle-test",
            nom="Test",
            prix_mensuel="0",
            devise="XOF",
            duree_essai_jours=14,
            actif=True,
        )
        self.entreprise = Entreprise.objects.create(
            raison_sociale="Entreprise Véhicules",
            devise="XOF",
            langue="fr",
            fuseau_horaire="Africa/Abidjan",
            statut_abonnement="essai",
            email_contact="vehicules@example.com",
            plan=plan,
        )
        role = Role.objects.create(
            entreprise=self.entreprise,
            code="admin",
            libelle="Administrateur",
        )
        self.user = User(
            nom="Admin Véhicules",
            email="admin.vehicules@example.com",
            statut="actif",
            entreprise=self.entreprise,
            role=role,
        )
        self.user.set_password("TestPassword123!")
        self.user.save()
        self.owner = Client.objects.create(
            code="CLI-TEST01",
            nom_complet="Jean Kouassi",
            adresse="Cocody",
            telephone="+2250700000000",
            entreprise=self.entreprise,
            user=self.user,
        )
        session = self.client.session
        session["utilisateur_id"] = self.user.pk
        session.save()

    def test_vehicle_crud_and_company_owner(self):
        response = self.client.post(reverse("vehicule:create"), {
            "client": self.owner.pk,
            "immatriculation": "ab-123-cd",
            "marque": "Toyota",
            "modele": "Corolla",
            "couleur": "Blanc",
            "type_vehicule": "Berline",
        })
        self.assertRedirects(response, reverse("vehicule:index"))
        vehicle = Vehicule.objects.get()
        self.assertEqual(vehicle.immatriculation, "AB-123-CD")
        self.assertEqual(vehicle.client, self.owner)
        self.assertEqual(vehicle.entreprise, self.entreprise)
        self.assertEqual(vehicle.created_by, self.user)

        response = self.client.get(reverse("vehicule:index"), {"q": "Toyota"})
        self.assertContains(response, "AB-123-CD")

        response = self.client.post(reverse("vehicule:update", args=[vehicle.pk]), {
            "client": self.owner.pk,
            "immatriculation": "AB-123-CD",
            "marque": "Toyota",
            "modele": "Corolla Cross",
            "couleur": "Noir",
            "type_vehicule": "SUV",
        })
        self.assertRedirects(response, reverse("vehicule:index"))
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.modele, "Corolla Cross")
        self.assertEqual(vehicle.updated_by, self.user)

        response = self.client.post(reverse("vehicule:delete", args=[vehicle.pk]))
        self.assertRedirects(response, reverse("vehicule:index"))
        vehicle.refresh_from_db()
        self.assertIsNotNone(vehicle.deleted_at)
        self.assertEqual(vehicle.deleted_by, self.user)
