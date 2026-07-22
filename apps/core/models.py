from django.db import models
from django.conf import settings
import base64
import hashlib
from cryptography.fernet import Fernet

from apps.entreprises.models import Entreprise


class Civilite(models.Model):
    entreprise = models.ForeignKey(
        Entreprise,
        on_delete=models.CASCADE,
        related_name="civilites",
    )
    code = models.CharField(max_length=20)
    libelle = models.CharField(max_length=80)
    actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "civilites"
        constraints = [
            models.UniqueConstraint(
                fields=["entreprise", "code"],
                name="uq_civilite_par_entreprise",
            ),
        ]

    def __str__(self):
        return self.libelle


class ConfigurationMail(models.Model):
    entreprise = models.OneToOneField(
        Entreprise,
        on_delete=models.CASCADE,
        related_name="configuration_mail",
    )
    nom_expediteur = models.CharField(max_length=120)
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
        db_table = "configurations_mail"

    @staticmethod
    def _fernet():
        key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(key))

    def set_password(self, value):
        if value:
            self.mot_de_passe_chiffre = self._fernet().encrypt(value.encode()).decode()

    def get_password(self):
        if not self.mot_de_passe_chiffre:
            return ""
        return self._fernet().decrypt(self.mot_de_passe_chiffre.encode()).decode()
