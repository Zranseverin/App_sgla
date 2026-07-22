from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.authentication.models import User
from apps.client.models import Client
from apps.caisse.models import MouvementCaisse
from apps.facture.models import Facture
from apps.entreprises.models import Entreprise
from apps.plan.models import Plan
from apps.roles.models import Role
from apps.type_lavage.models import TypeLavage
from apps.vehicule.models import Vehicule

from .models import Passage


class PassageTests(TestCase):
    def setUp(self):
        plan = Plan.objects.create(code="passage-test", nom="Test", prix_mensuel="0", devise="XOF", duree_essai_jours=14, actif=True)
        self.entreprise = Entreprise.objects.create(raison_sociale="Station Test", devise="XOF", langue="fr", fuseau_horaire="Africa/Abidjan", statut_abonnement="essai", email_contact="station@example.com", plan=plan)
        role = Role.objects.create(entreprise=self.entreprise, code="laveur", libelle="Laveur")
        self.user = User(nom="Admin Station", email="admin@station.test", statut="actif", entreprise=self.entreprise, role=role)
        self.user.set_password("TestPassword123!")
        self.user.save()
        self.client_record = Client.objects.create(code="CLI-PASS01", nom_complet="Client Passage", adresse="Abidjan", telephone="+2250700000000", entreprise=self.entreprise, user=self.user)
        self.vehicle = Vehicule.objects.create(immatriculation="AB-100-CD", client=self.client_record, entreprise=self.entreprise, user=self.user)
        self.wash_type = TypeLavage.objects.create(libelle="Lavage complet", prix_unitaire="10000", actif=True, entreprise=self.entreprise, user=self.user)
        session = self.client.session
        session["utilisateur_id"] = self.user.pk
        session.save()

    def test_passage_crud_and_financial_validation(self):
        started = timezone.localtime().strftime("%Y-%m-%dT%H:%M")
        payload = {
            "date_heure_debut": started,
            "client": self.client_record.pk,
            "vehicule": self.vehicle.pk,
            "type_lavage": self.wash_type.pk,
            "piste_id": "1",
            "forfait_id": "",
            "employe_realisateur": self.user.pk,
            "caissier": self.user.pk,
            "montant_total": "10000",
            "montant_paye": "6000",
            "montant_partiel_verse": "6000",
            "montant_restant": "4000",
            "commission_employe": "1800",
            "net_station": "4200",
            "mode_reglement": "especes",
            "statut_reglement": "partiel",
            "statut": "en_cours",
            "date_heure_fin": "",
            "date_annulation": "",
            "motif_annulation": "",
        }
        response = self.client.post(reverse("passage:create"), payload)
        passage = Passage.objects.get()
        facture = Facture.objects.get(passage=passage)
        self.assertRedirects(response, reverse("facture:detail", args=[facture.pk]))
        self.assertEqual(passage.entreprise, self.entreprise)
        self.assertEqual(passage.created_by, self.user)
        self.assertEqual(passage.caissier, self.user)
        self.assertEqual(passage.montant_total, Decimal("10000"))
        self.assertEqual(passage.montant_paye, Decimal("6000"))
        self.assertEqual(passage.commission_employe, Decimal("1200"))
        self.assertEqual(passage.net_station, Decimal("4800"))
        self.assertEqual(facture.client, self.client_record)
        self.assertEqual(facture.montant_total, Decimal("10000"))
        self.assertEqual(facture.montant_paye, Decimal("6000"))
        self.assertEqual(facture.statut, "partiel")
        pdf_response = self.client.get(reverse("facture:pdf", args=[facture.pk]))
        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(pdf_response["Content-Type"], "application/pdf")
        self.assertTrue(pdf_response.content.startswith(b"%PDF-1.4"))
        mouvement = MouvementCaisse.objects.get(passage=passage)
        self.assertEqual(mouvement.type_mouvement, "entree")
        self.assertEqual(mouvement.montant, Decimal("6000"))

        response = self.client.post(
            reverse("caisse:encaisser_passage", args=[passage.pk]),
            {"montant": "4000", "mode_reglement": "wave"},
        )
        self.assertRedirects(response, reverse("caisse:index"))
        passage.refresh_from_db()
        self.assertEqual(passage.statut_reglement, "paye")
        self.assertEqual(passage.montant_paye, Decimal("10000"))
        facture.refresh_from_db()
        self.assertEqual(facture.montant_paye, Decimal("10000"))
        self.assertEqual(facture.statut, "paye")
        mouvement.refresh_from_db()
        self.assertEqual(mouvement.montant, Decimal("10000"))

        response = self.client.get(reverse("passage:index"), {"q": "AB-100"})
        self.assertContains(response, "Client Passage")

        payload.update({"statut": "termine", "montant_paye": "10000", "montant_restant": "0", "commission_employe": "3000", "net_station": "7000", "statut_reglement": "paye"})
        response = self.client.post(reverse("passage:update", args=[passage.pk]), payload)
        self.assertRedirects(response, reverse("passage:index"))
        passage.refresh_from_db()
        self.assertEqual(passage.statut, "termine")
        self.assertEqual(passage.updated_by, self.user)
        self.assertEqual(passage.commission_employe, Decimal("2000"))
        self.assertEqual(passage.net_station, Decimal("8000"))
        mouvement.refresh_from_db()
        self.assertEqual(mouvement.montant, Decimal("10000"))

        response = self.client.post(reverse("passage:delete", args=[passage.pk]))
        self.assertRedirects(response, reverse("passage:index"))
        passage.refresh_from_db()
        self.assertIsNotNone(passage.deleted_at)

    def test_vehicle_dropdown_returns_only_selected_client_vehicles(self):
        other_client = Client.objects.create(
            code="CLI-PASS02",
            nom_complet="Autre Client",
            adresse="Yopougon",
            telephone="+2250500000000",
            entreprise=self.entreprise,
            user=self.user,
        )
        other_vehicle = Vehicule.objects.create(
            immatriculation="XY-999-ZZ",
            client=other_client,
            entreprise=self.entreprise,
            user=self.user,
        )

        response = self.client.get(
            reverse(
                "passage:vehicles_by_client",
                args=[self.client_record.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        vehicle_ids = {
            vehicle["id"] for vehicle in response.json()["vehicules"]
        }
        self.assertIn(self.vehicle.pk, vehicle_ids)
        self.assertNotIn(other_vehicle.pk, vehicle_ids)

        response = self.client.get(reverse("passage:create"))
        self.assertContains(response, "vehicules-par-client")
        self.assertContains(response, "id_client")
        self.assertContains(response, "id_vehicule")
        self.assertContains(response, "setVehicleMode('existing')")

    def test_employee_realisateur_contains_only_active_washers(self):
        admin_role = Role.objects.create(
            entreprise=self.entreprise,
            code="admin",
            libelle="Administrateur",
        )
        admin = User.objects.create(
            nom="Autre Administrateur",
            email="other-admin@station.test",
            password="unused",
            statut="actif",
            entreprise=self.entreprise,
            role=admin_role,
        )

        response = self.client.get(reverse("passage:create"))
        queryset = response.context["form"].fields["employe_realisateur"].queryset

        self.assertIn(self.user, queryset)
        self.assertNotIn(admin, queryset)

    def test_create_passage_with_new_client_and_new_vehicle(self):
        response = self.client.post(reverse("passage:create"), {
            "client_mode": "new",
            "new_client_nom_complet": "Aya Konan",
            "new_client_telephone": "+2250102030405",
            "new_client_email": "aya@example.com",
            "new_client_adresse": "Marcory, Abidjan",
            "vehicule_mode": "new",
            "new_vehicle_immatriculation": "ci-024-abc",
            "new_vehicle_type_vehicule": "SUV",
            "new_vehicle_marque": "Hyundai",
            "new_vehicle_modele": "Tucson",
            "new_vehicle_couleur": "Grise",
            "date_heure_debut": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            "type_lavage": self.wash_type.pk,
            "forfait_id": "",
            "employe_realisateur": self.user.pk,
            "caissier": self.user.pk,
            "mode_reglement": "especes",
            "statut_reglement": "paye",
            "statut": "en_cours",
        })

        new_client = Client.objects.get(telephone="+2250102030405")
        new_vehicle = Vehicule.objects.get(immatriculation="CI-024-ABC")
        passage = Passage.objects.get(client=new_client)
        self.assertRedirects(response, reverse("facture:detail", args=[passage.facture.pk]))
        self.assertEqual(new_vehicle.client, new_client)
        self.assertEqual(passage.vehicule, new_vehicle)
        self.assertIsNone(passage.piste_id)
        self.assertEqual(new_client.entreprise, self.entreprise)
        self.assertEqual(new_vehicle.entreprise, self.entreprise)

    def test_new_entry_data_overrides_stale_existing_modes(self):
        response = self.client.post(reverse("passage:create"), {
            "client_mode": "existing",
            "client": self.client_record.pk,
            "new_client_nom_complet": "Awa Traore",
            "new_client_telephone": "+2250701020304",
            "new_client_adresse": "Cocody",
            "vehicule_mode": "existing",
            "vehicule": self.vehicle.pk,
            "new_vehicle_immatriculation": "CI-777-ZZ",
            "new_vehicle_type_vehicule": "BERLINE",
            "date_heure_debut": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            "type_lavage": self.wash_type.pk,
            "piste_id": "3",
            "employe_realisateur": self.user.pk,
            "caissier": self.user.pk,
            "mode_reglement": "especes",
            "statut_reglement": "paye",
            "statut": "en_cours",
        })

        passage = Passage.objects.get(client__telephone="+2250701020304")
        self.assertRedirects(response, reverse("facture:detail", args=[passage.facture.pk]))
        self.assertEqual(passage.client.nom_complet, "Awa Traore")
        self.assertEqual(passage.vehicule.immatriculation, "CI-777-ZZ")
        self.assertNotEqual(passage.client, self.client_record)
        self.assertNotEqual(passage.vehicule, self.vehicle)

    def test_new_client_vehicle_validation_is_displayed_and_atomic(self):
        response = self.client.post(reverse("passage:create"), {
            "client_mode": "new",
            "new_client_nom_complet": "Client en double",
            "new_client_telephone": self.client_record.telephone,
            "new_client_adresse": "Abidjan",
            "vehicule_mode": "new",
            "new_vehicle_immatriculation": "NEW-001",
            "date_heure_debut": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            "type_lavage": self.wash_type.pk,
            "piste_id": "2",
            "employe_realisateur": self.user.pk,
            "caissier": self.user.pk,
            "mode_reglement": "especes",
            "statut_reglement": "paye",
            "statut": "en_cours",
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Un client existe")
        self.assertContains(response, 'value="new"')
        self.assertFalse(Vehicule.objects.filter(immatriculation="NEW-001").exists())
        self.assertFalse(Passage.objects.exists())
