from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from apps.plan.models import Plan
from django.utils import timezone


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
    date_debut_abonnement = models.DateField(null=True, blank=True)
    date_fin_abonnement = models.DateField(null=True, blank=True)
    email_contact = models.EmailField(max_length=150)
    telephone_contact = models.CharField(max_length=30, null=True, blank=True)
    adresse = models.CharField(max_length=255, null=True, blank=True)
    commune = models.CharField(max_length=100, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
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

    @property
    def date_fin_acces(self):
        if self.statut_abonnement == "essai":
            return self.date_fin_essai
        if self.statut_abonnement == "actif":
            return self.date_fin_abonnement
        return None

    def abonnement_est_actif(self, date=None):
        """Retourne vrai si l'entreprise peut encore utiliser l'application."""
        date = date or timezone.localdate()
        date_fin = self.date_fin_acces
        return (
            self.statut_abonnement in {"essai", "actif"}
            and date_fin is not None
            and date_fin >= date
        )


class VisitorEvent(models.Model):
    EVENT_TYPES = [
        ("page_view", "Consultation de page"),
        ("search", "Recherche"),
        ("geolocation_request", "Clic sur Me localiser"),
        ("geolocation_success", "Localisation autorisée"),
        ("company_view", "Entreprise consultée"),
        ("catalog_view", "Catalogue consulté"),
        ("route_request", "Itinéraire demandé"),
    ]

    event_type = models.CharField(max_length=24, choices=EVENT_TYPES)
    visitor_id = models.CharField(max_length=64, db_index=True)
    session_key = models.CharField(max_length=40, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_label = models.CharField(max_length=120, blank=True)
    user_agent = models.TextField(blank=True)
    page_path = models.CharField(max_length=255, blank=True)
    referrer = models.URLField(max_length=500, blank=True)
    search_query = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    locality = models.CharField(max_length=180, blank=True)
    entreprise = models.ForeignKey(Entreprise, on_delete=models.SET_NULL, null=True, blank=True, related_name="visitor_events")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "visitor_events"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_event_type_display()} · {self.visitor_id}"
