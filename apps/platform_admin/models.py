import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class CleanGoAdmin(models.Model):
    STATUTS = [("actif", "Actif"), ("inactif", "Inactif")]

    nom = models.CharField(max_length=120)
    email = models.EmailField(max_length=150, unique=True)
    password = models.CharField(max_length=255)
    telephone = models.CharField(max_length=30, blank=True)
    statut = models.CharField(max_length=7, choices=STATUTS, default="actif")
    derniere_connexion = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cleango_admins"
        ordering = ["nom"]

    def __str__(self):
        return f"{self.nom} ({self.email})"

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)


class CleanGoMailConfiguration(models.Model):
    nom_expediteur = models.CharField(max_length=120, default="CleanGo")
    email_expediteur = models.EmailField(max_length=150)
    serveur_smtp = models.CharField(max_length=150, default="smtp.gmail.com")
    port_smtp = models.PositiveIntegerField(default=465)
    utilisateur_smtp = models.CharField(max_length=150)
    mot_de_passe_chiffre = models.TextField(blank=True)
    utiliser_tls = models.BooleanField(default=False)
    utiliser_ssl = models.BooleanField(default=True)
    actif = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cleango_configuration_mail"

    @staticmethod
    def _fernet():
        secret = getattr(settings, "MAIL_ENCRYPTION_KEY", settings.SECRET_KEY)
        key = hashlib.sha256(secret.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(key))

    def set_password(self, value):
        if value:
            self.mot_de_passe_chiffre = self._fernet().encrypt(value.encode()).decode()

    def get_password(self):
        if not self.mot_de_passe_chiffre:
            return ""
        return self._fernet().decrypt(self.mot_de_passe_chiffre.encode()).decode()


class SubscriptionEmailLog(models.Model):
    TYPES = [
        ("expiration", "Rappel d’expiration"),
        ("paiement", "Confirmation de paiement"),
    ]

    reference = models.CharField(max_length=120, unique=True)
    entreprise = models.ForeignKey(
        "entreprises.Entreprise",
        on_delete=models.CASCADE,
        related_name="notifications_abonnement",
    )
    type_notification = models.CharField(max_length=12, choices=TYPES)
    destinataires = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cleango_subscription_email_logs"
        ordering = ["-sent_at"]
