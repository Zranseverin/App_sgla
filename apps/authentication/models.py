from django.db import models
from django.contrib.auth.hashers import check_password, make_password
from apps.entreprises.models import Entreprise
from apps.roles.models import Role


class User(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    nom = models.CharField(max_length=100)
    email = models.EmailField(max_length=150)
    matricule = models.CharField(max_length=20, null=True, blank=True)
    telephone = models.CharField(max_length=30, null=True, blank=True)
    adresse = models.CharField(max_length=255, null=True, blank=True)
    civilite = models.ForeignKey(
        "core.Civilite",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="utilisateurs",
    )
    photo = models.ImageField(upload_to="utilisateurs/photos/", null=True, blank=True)
    password = models.CharField(max_length=255)
    statut = models.CharField(max_length=7)
    entreprise = models.ForeignKey(
        Entreprise,
        on_delete=models.PROTECT,
        db_column="entreprise_id",
        related_name="utilisateurs",
    )
    invite_par = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        db_column="invite_par_id",
        null=True,
        blank=True,
        related_name="utilisateurs_invites",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        db_column="role_id",
        related_name="utilisateurs",
    )

    class Meta:
        db_table = "user"
        constraints = [
            models.UniqueConstraint(
                fields=["entreprise", "matricule"],
                name="uq_matricule_par_entreprise",
            ),
        ]

    def __str__(self):
        return f"{self.nom} ({self.email})"

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)
