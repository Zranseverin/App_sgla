import re
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.entreprises.models import Entreprise
from apps.core.models import Civilite, ConfigurationMail
from apps.plan.models import PaiementAbonnement, Plan
from apps.roles.models import Role

from .models import User


TINY_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
    b"\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,"
    b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


def uploaded_image(name):
    return SimpleUploadedFile(name, TINY_GIF, content_type="image/gif")


class CompanyRegistrationTests(TestCase):
    def setUp(self):
        self.plan = Plan.objects.create(
            code="starter-test",
            nom="Starter",
            description="Plan de test",
            prix_mensuel="15000.00",
            devise="XOF",
            max_centres=1,
            max_utilisateurs=5,
            quota_sms_mensuel=100,
            duree_essai_jours=14,
            actif=True,
        )
        self.url = reverse("authentication:inscription")

    def test_registration_page_lists_active_plans(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Starter")
        self.assertContains(response, "Créer mon entreprise")

    def test_registration_creates_company_roles_admin_and_trial(self):
        response = self.client.post(self.url, {
            "nom": "Awa Koné",
            "email": "awa@example.com",
            "password": "MotDePasse123!",
            "confirm_password": "MotDePasse123!",
            "entreprise_nom": "Lavage Ivoire",
            "telephone_contact": "+2250102030405",
            "logo_url": uploaded_image("logo.gif"),
            "couleur_principale": "#123ABC",
            "devise": "XOF",
            "langue": "fr",
            "fuseau_horaire": "Africa/Abidjan",
            "plan": self.plan.pk,
        })

        self.assertRedirects(response, reverse("authentication:connexion"))
        entreprise = Entreprise.objects.get(raison_sociale="Lavage Ivoire")
        self.assertEqual(entreprise.plan, self.plan)
        self.assertEqual(entreprise.statut_abonnement, "essai")
        self.assertEqual((entreprise.date_fin_essai - entreprise.date_debut_essai).days, 14)
        self.assertEqual(entreprise.couleur_principale, "#123ABC")
        self.assertEqual(Role.objects.filter(entreprise=entreprise).count(), 4)

        admin = User.objects.get(email="awa@example.com")
        self.assertEqual(admin.entreprise, entreprise)
        self.assertEqual(admin.role.code, "admin")
        self.assertTrue(admin.check_password("MotDePasse123!"))

    def test_duplicate_email_does_not_create_another_company(self):
        role = Role.objects.create(code="admin", libelle="Administrateur")
        entreprise = Entreprise.objects.create(
            raison_sociale="Entreprise existante",
            devise="XOF",
            langue="fr",
            fuseau_horaire="Africa/Abidjan",
            statut_abonnement="essai",
            email_contact="existant@example.com",
            plan=self.plan,
        )
        user = User(
            nom="Client existant",
            email="existant@example.com",
            statut="actif",
            entreprise=entreprise,
            role=role,
        )
        user.set_password("MotDePasse123!")
        user.save()

        response = self.client.post(self.url, {
            "nom": "Autre client",
            "email": "EXISTANT@example.com",
            "password": "MotDePasse123!",
            "confirm_password": "MotDePasse123!",
            "entreprise_nom": "Entreprise doublon",
            "couleur_principale": "#0E7C86",
            "devise": "XOF",
            "langue": "fr",
            "fuseau_horaire": "Africa/Abidjan",
            "plan": self.plan.pk,
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Entreprise.objects.filter(raison_sociale="Entreprise doublon").exists())


class PasswordResetTests(TestCase):
    def setUp(self):
        plan = Plan.objects.create(
            code="reset-test",
            nom="Reset",
            prix_mensuel="0.00",
            devise="XOF",
            duree_essai_jours=14,
            actif=True,
        )
        entreprise = Entreprise.objects.create(
            raison_sociale="Entreprise Reset",
            devise="XOF",
            langue="fr",
            fuseau_horaire="Africa/Abidjan",
            statut_abonnement="essai",
            email_contact="reset@example.com",
            plan=plan,
        )
        role = Role.objects.create(
            entreprise=entreprise,
            code="admin",
            libelle="Administrateur",
        )
        self.user = User(
            nom="Client Reset",
            email="reset@example.com",
            statut="actif",
            entreprise=entreprise,
            role=role,
        )
        self.user.set_password("AncienMotDePasse123!")
        self.user.save()

    def test_request_sends_reset_email_and_does_not_disclose_unknown_email(self):
        response = self.client.post(
            reverse("authentication:forgot_password"),
            {"email": self.user.email},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("réinitialisation", mail.outbox[0].subject.lower())

        self.client.post(
            reverse("authentication:forgot_password"),
            {"email": "inconnu@example.com"},
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_password_reset_uses_connected_company_smtp_configuration(self):
        config = ConfigurationMail.objects.create(
            entreprise=self.user.entreprise,
            nom_expediteur=self.user.entreprise.raison_sociale,
            email_expediteur="noreply@example.com",
            serveur_smtp="smtp.example.com",
            port_smtp=465,
            utilisateur_smtp="noreply@example.com",
            utiliser_ssl=True,
            actif=True,
        )
        config.set_password("smtp-secret")
        config.save()

        with patch("apps.authentication.views.yagmail.SMTP") as smtp_class:
            response = self.client.post(
                reverse("authentication:forgot_password"),
                {"email": self.user.email},
            )

        self.assertRedirects(response, reverse("authentication:connexion"))
        smtp_class.assert_called_once()
        sent = smtp_class.return_value.send.call_args.kwargs
        self.assertEqual(sent["to"], self.user.email)
        self.assertIn("/reinitialiser/", sent["contents"])
        self.assertIn("Réinitialiser mon mot de passe", sent["contents"])
        self.assertIn("<!doctype html>", sent["contents"])
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_changes_password_and_invalidates_used_link(self):
        self.client.post(
            reverse("authentication:forgot_password"),
            {"email": self.user.email},
        )
        match = re.search(r"/reinitialiser/([^/\s]+)/", mail.outbox[0].body)
        self.assertIsNotNone(match)
        token = match.group(1)
        reset_url = reverse("authentication:reset_password", kwargs={"token": token})

        response = self.client.post(reset_url, {
            "new_password": "NouveauMotDePasse123!",
            "confirm_password": "NouveauMotDePasse123!",
        })
        self.assertRedirects(response, reverse("authentication:connexion"))

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NouveauMotDePasse123!"))
        self.assertEqual(self.client.get(reset_url).status_code, 400)


class DashboardTests(TestCase):
    def setUp(self):
        plan = Plan.objects.create(
            code="dashboard-test",
            nom="Pro",
            prix_mensuel="35000.00",
            devise="XOF",
            max_centres=5,
            max_utilisateurs=25,
            quota_sms_mensuel=500,
            duree_essai_jours=14,
            actif=True,
        )
        entreprise = Entreprise.objects.create(
            raison_sociale="SGLA Démonstration",
            couleur_principale="#1769D2",
            devise="XOF",
            langue="fr",
            fuseau_horaire="Africa/Abidjan",
            statut_abonnement="essai",
            email_contact="dashboard@example.com",
            plan=plan,
        )
        role = Role.objects.create(
            entreprise=entreprise,
            code="admin",
            libelle="Administrateur",
        )
        self.user = User(
            nom="Awa Koné",
            email="dashboard@example.com",
            statut="actif",
            entreprise=entreprise,
            role=role,
        )
        self.user.set_password("MotDePasse123!")
        self.user.save()
        self.url = reverse("dashboard:index")

    def test_dashboard_requires_application_session(self):
        response = self.client.get(self.url)
        self.assertRedirects(
            response,
            reverse("authentication:connexion"),
            fetch_redirect_response=False,
        )

    def test_dashboard_renders_layout_and_company_data(self):
        session = self.client.session
        session["utilisateur_id"] = self.user.pk
        session.save()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/index.html")
        self.assertTemplateUsed(response, "dashboard/partials/header.html")
        self.assertTemplateUsed(response, "dashboard/partials/sidebar.html")
        self.assertContains(response, "LOGITRUCK")
        self.assertContains(response, "KOUASSI JEAN")
        self.assertContains(response, "Recherche & Reporting")

    def test_profile_page_requires_session_and_shows_edit_button(self):
        response = self.client.get(reverse("authentication:profile"))
        self.assertRedirects(
            response,
            reverse("authentication:connexion"),
            fetch_redirect_response=False,
        )

        session = self.client.session
        session["utilisateur_id"] = self.user.pk
        session.save()
        response = self.client.get(reverse("authentication:profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Modifier le profil")
        self.assertContains(response, self.user.nom)
        self.assertContains(response, self.user.entreprise.raison_sociale)

    def test_connected_user_can_edit_profile(self):
        session = self.client.session
        session["utilisateur_id"] = self.user.pk
        session.save()

        response = self.client.post(reverse("authentication:edit_profile"), {
            "nom": "Awa Koné Modifié",
            "email": "awa.modifiee@example.com",
            "photo": uploaded_image("awa-photo.gif"),
        })

        self.assertRedirects(response, reverse("authentication:profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.nom, "Awa Koné Modifié")
        self.assertEqual(self.user.email, "awa.modifiee@example.com")
        self.assertIn("utilisateurs/photos/awa-photo", self.user.photo.name)

        response = self.client.get(reverse("authentication:profile"))
        self.assertContains(response, self.user.photo.url)

    def test_admin_can_view_and_edit_enterprise_profile(self):
        session = self.client.session
        session["utilisateur_id"] = self.user.pk
        session.save()

        response = self.client.get(reverse("authentication:enterprise_settings"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Modifier l’entreprise")

        response = self.client.post(
            reverse("authentication:edit_enterprise_settings"),
            {
                "raison_sociale": "Nouvelle Société SGLA",
                "slogan": "Toujours plus propre",
                "logo_url": uploaded_image("logo.gif"),
                "favicon_url": uploaded_image("favicon.gif"),
                "couleur_principale": "#123ABC",
                "email_contact": "contact@nouvelle-sgla.com",
                "telephone_contact": "+2250102030405",
                "devise": "XOF",
                "langue": "fr",
                "fuseau_horaire": "Africa/Abidjan",
            },
        )
        self.assertRedirects(response, reverse("authentication:enterprise_settings"))
        self.user.entreprise.refresh_from_db()
        self.assertEqual(self.user.entreprise.raison_sociale, "Nouvelle Société SGLA")
        self.assertEqual(self.user.entreprise.slogan, "Toujours plus propre")
        self.assertEqual(self.user.entreprise.couleur_principale, "#123ABC")

    def test_enterprise_profile_shows_only_connected_company_payment_history(self):
        own_payment = PaiementAbonnement.objects.create(
            entreprise=self.user.entreprise,
            plan=self.user.entreprise.plan,
            methode="orange",
            telephone="+2250700000000",
            montant=self.user.entreprise.plan.prix_mensuel,
            devise="XOF",
            statut="paye",
        )
        other_company = Entreprise.objects.create(
            raison_sociale="Entreprise externe",
            couleur_principale="#222222",
            devise="XOF",
            langue="fr",
            fuseau_horaire="Africa/Abidjan",
            statut_abonnement="actif",
            email_contact="autre@example.com",
            plan=self.user.entreprise.plan,
        )
        other_payment = PaiementAbonnement.objects.create(
            entreprise=other_company,
            plan=other_company.plan,
            methode="wave",
            telephone="+2250500000000",
            montant=other_company.plan.prix_mensuel,
            devise="XOF",
        )
        session = self.client.session
        session["utilisateur_id"] = self.user.pk
        session.save()

        response = self.client.get(reverse("authentication:enterprise_settings"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Historique des abonnements")
        self.assertContains(response, "Historique des paiements")
        self.assertContains(response, own_payment.reference)
        self.assertNotContains(response, other_payment.reference)

    def test_non_admin_cannot_edit_enterprise_profile(self):
        self.user.role.code = "manager"
        self.user.role.save(update_fields=["code"])
        session = self.client.session
        session["utilisateur_id"] = self.user.pk
        session.save()

        response = self.client.get(reverse("authentication:edit_enterprise_settings"))

        self.assertRedirects(response, reverse("authentication:enterprise_settings"))

    def test_configuration_page_displays_the_four_tabs(self):
        session = self.client.session
        session["utilisateur_id"] = self.user.pk
        session.save()

        response = self.client.get(reverse("authentication:configuration"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "authentication/configuration.html")
        self.assertContains(response, "?tab=accounts")
        self.assertContains(response, "?tab=enterprise")
        self.assertContains(response, "?tab=roles")
        self.assertContains(response, "?tab=civilities")
        self.assertContains(response, "?tab=subscription")
        self.assertContains(response, "?tab=mail")

    def test_admin_can_save_company_mail_configuration_with_encrypted_password(self):
        session = self.client.session
        session["utilisateur_id"] = self.user.pk
        session.save()
        url = reverse("authentication:configuration")

        response = self.client.post(url, {
            "action": "save_mail_configuration",
            "nom_expediteur": "SGLA Démonstration",
            "email_expediteur": "noreply@example.com",
            "serveur_smtp": "smtp.gmail.com",
            "port_smtp": "465",
            "utilisateur_smtp": "noreply@example.com",
            "mot_de_passe": "mot-de-passe-application",
            "utiliser_ssl": "on",
            "actif": "on",
        })

        self.assertRedirects(response, f"{url}?tab=mail")
        config = ConfigurationMail.objects.get(entreprise=self.user.entreprise)
        self.assertNotEqual(
            config.mot_de_passe_chiffre,
            "mot-de-passe-application",
        )
        self.assertEqual(config.get_password(), "mot-de-passe-application")

    def test_subscription_tab_detects_an_expired_trial_and_lists_plans(self):
        self.user.entreprise.date_fin_essai = timezone.localdate() - timedelta(days=1)
        self.user.entreprise.statut_abonnement = "essai"
        self.user.entreprise.save(
            update_fields=["date_fin_essai", "statut_abonnement"]
        )
        session = self.client.session
        session["utilisateur_id"] = self.user.pk
        session.save()

        response = self.client.get(
            f"{reverse('authentication:configuration')}?tab=subscription"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Votre essai gratuit est terminé")
        self.assertContains(response, self.user.entreprise.plan.nom)
        self.assertContains(response, "Choisir et payer")
        self.assertContains(response, "MTN Mobile Money")
        self.assertContains(response, "Wave")
        self.assertContains(response, "Orange Money")
        self.assertContains(response, "Moov Money")
        self.assertContains(response, "Visa / Mastercard")

    def test_admin_can_initiate_mobile_subscription_payment(self):
        session = self.client.session
        session["utilisateur_id"] = self.user.pk
        session.save()
        url = reverse("authentication:configuration")

        response = self.client.post(url, {
            "action": "initiate_payment",
            "plan_id": self.user.entreprise.plan_id,
            "methode": "wave",
            "telephone": "+2250700000000",
        })

        self.assertRedirects(response, f"{url}?tab=subscription")
        payment = PaiementAbonnement.objects.get(entreprise=self.user.entreprise)
        self.assertEqual(payment.methode, "wave")
        self.assertEqual(payment.statut, "en_attente")
        self.assertTrue(payment.reference.startswith("PAY-"))

    def test_admin_can_create_role_and_civility_from_configuration(self):
        session = self.client.session
        session["utilisateur_id"] = self.user.pk
        session.save()
        url = reverse("authentication:configuration")

        role_response = self.client.post(url, {
            "action": "create_role",
            "libelle": "Superviseur",
        })
        self.assertRedirects(role_response, f"{url}?tab=roles")
        created_role = Role.objects.get(
            entreprise=self.user.entreprise,
            libelle="Superviseur",
        )
        self.assertRegex(created_role.code, r"^ROLE-[A-F0-9]{6}$")

        civility_response = self.client.post(url, {
            "action": "create_civilite",
            "libelle": "Madame",
            "actif": "on",
        })
        self.assertRedirects(civility_response, f"{url}?tab=civilities")
        civility = Civilite.objects.get(
            entreprise=self.user.entreprise,
            libelle="Madame",
        )
        self.assertRegex(civility.code, r"^CIV-[A-F0-9]{6}$")

    def test_admin_can_create_user_from_configuration(self):
        civility = Civilite.objects.create(
            entreprise=self.user.entreprise,
            code="CIV-TEST01",
            libelle="Madame",
            actif=True,
        )
        mail_config = ConfigurationMail.objects.create(
            entreprise=self.user.entreprise,
            nom_expediteur=self.user.entreprise.raison_sociale,
            email_expediteur="noreply@example.com",
            serveur_smtp="smtp.example.com",
            port_smtp=465,
            utilisateur_smtp="noreply@example.com",
            utiliser_ssl=True,
            actif=True,
        )
        mail_config.set_password("smtp-secret")
        mail_config.save()
        session = self.client.session
        session["utilisateur_id"] = self.user.pk
        session.save()
        url = reverse("authentication:configuration")

        with patch("apps.authentication.views.yagmail.SMTP") as smtp_class:
            response = self.client.post(url, {
                "action": "create_account",
                "nom": "Jean Kouassi",
                "email": "jean.kouassi@example.com",
                "civilite": civility.pk,
                "telephone": "+2250700000000",
                "adresse": "Cocody, Abidjan",
                "role": self.user.role_id,
            })

        self.assertRedirects(response, f"{url}?tab=accounts")
        created_user = User.objects.get(email="jean.kouassi@example.com")
        self.assertEqual(created_user.entreprise, self.user.entreprise)
        self.assertEqual(created_user.invite_par, self.user)
        self.assertEqual(created_user.statut, "actif")
        self.assertEqual(created_user.civilite, civility)
        self.assertEqual(created_user.telephone, "+2250700000000")
        self.assertEqual(created_user.adresse, "Cocody, Abidjan")
        self.assertRegex(created_user.matricule, r"^MAT-[A-F0-9]{6}$")
        smtp_class.return_value.send.assert_called_once()
        sent_message = smtp_class.return_value.send.call_args.kwargs
        self.assertEqual(sent_message["to"], "jean.kouassi@example.com")
        sent_contents = sent_message["contents"]
        generated_password = re.search(
            r"Mot de passe initial : ([^\s]+)",
            sent_contents,
        ).group(1)
        self.assertIn("Se connecter à mon espace", sent_contents)
        self.assertIn("<!doctype html>", sent_contents)
        self.assertGreaterEqual(len(generated_password), 16)
        self.assertTrue(created_user.check_password(generated_password))

    def test_collaborator_is_not_created_when_invitation_email_fails(self):
        civility = Civilite.objects.create(
            entreprise=self.user.entreprise,
            code="CIV-TEST02",
            libelle="Monsieur",
            actif=True,
        )
        mail_config = ConfigurationMail.objects.create(
            entreprise=self.user.entreprise,
            nom_expediteur=self.user.entreprise.raison_sociale,
            email_expediteur="noreply@example.com",
            serveur_smtp="smtp.example.com",
            port_smtp=465,
            utilisateur_smtp="noreply@example.com",
            utiliser_ssl=True,
            actif=True,
        )
        mail_config.set_password("smtp-secret")
        mail_config.save()
        session = self.client.session
        session["utilisateur_id"] = self.user.pk
        session.save()

        with patch(
            "apps.authentication.views.yagmail.SMTP",
            side_effect=OSError("SMTP unavailable"),
        ):
            response = self.client.post(reverse("authentication:configuration"), {
                "action": "create_account",
                "nom": "Compte Non Envoyé",
                "email": "non.envoye@example.com",
                "civilite": civility.pk,
                "telephone": "+2250500000000",
                "adresse": "Marcory, Abidjan",
                "role": self.user.role_id,
            })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "email d’invitation")
        self.assertFalse(User.objects.filter(email="non.envoye@example.com").exists())
