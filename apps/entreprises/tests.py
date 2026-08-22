from django.test import TestCase
from django.urls import reverse

from apps.plan.models import Plan
from .models import Entreprise


class PublicDirectoryTests(TestCase):
    def setUp(self):
        plan = Plan.objects.create(
            code="directory-test",
            nom="Annuaire",
            prix_mensuel=0,
            devise="XOF",
            duree_essai_jours=14,
            actif=True,
        )
        self.visible = Entreprise.objects.create(
            raison_sociale="Lavage Étoile",
            slogan="Votre voiture toujours propre",
            devise="XOF",
            langue="fr",
            fuseau_horaire="Africa/Abidjan",
            statut_abonnement="actif",
            email_contact="etoile@example.com",
            telephone_contact="+2250102030405",
            plan=plan,
        )
        Entreprise.objects.create(
            raison_sociale="Entreprise suspendue",
            devise="XOF",
            langue="fr",
            fuseau_horaire="Africa/Abidjan",
            statut_abonnement="suspendu",
            email_contact="suspendue@example.com",
            plan=plan,
        )

    def test_directory_lists_only_available_companies(self):
        response = self.client.get(reverse("public_directory"))
        self.assertContains(response, "Lavage Étoile")
        self.assertNotContains(response, "Entreprise suspendue")
        self.assertContains(response, reverse("authentication:connexion"))

    def test_directory_search(self):
        response = self.client.get(reverse("public_directory"), {"q": "Étoile"})
        self.assertContains(response, "Lavage Étoile")
        response = self.client.get(reverse("public_directory"), {"q": "introuvable"})
        self.assertContains(response, "Aucune entreprise trouvée")
