from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from apps.plan.models import Plan


class Entreprise(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    raison_sociale = models.CharField(max_length=150)
    logo_url = models.ImageField(upload_to="entreprises/logos/", null=True, blank=True)
    favicon_url = models.ImageField(upload_to="entreprises/favicons/", null=True, blank=True)
    slogan = models.CharField(max_length=180, null=True, blank=True)
    couleur_principale = models.CharField(max_length=7, null=True, blank=True)
    devise = models.CharField(max_length=3)
    langue = models.CharField(max_length=5)
    fuseau_horaire = models.CharField(max_length=50)
    statut_abonnement = models.CharField(max_length=8)
    date_debut_essai = models.DateField(null=True, blank=True)
    date_fin_essai = models.DateField(null=True, blank=True)
    email_contact = models.EmailField(max_length=150)
    telephone_contact = models.CharField(max_length=30, null=True, blank=True)
    taux_commission_laveur = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=20,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        db_column="plan_id",
        related_name="entreprises",
    )

    class Meta:
        db_table = "entreprises"

    def __str__(self):
        return self.raison_sociale
