from django.db import models
import uuid


class Plan(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    code = models.CharField(max_length=30)
    nom = models.CharField(max_length=100)
    description = models.CharField(max_length=255, null=True, blank=True)
    prix_mensuel = models.DecimalField(max_digits=10, decimal_places=2)
    devise = models.CharField(max_length=3)
    max_centres = models.PositiveSmallIntegerField(null=True, blank=True)
    max_utilisateurs = models.PositiveSmallIntegerField(null=True, blank=True)
    quota_sms_mensuel = models.PositiveIntegerField(null=True, blank=True)
    duree_essai_jours = models.PositiveSmallIntegerField()
    actif = models.BooleanField()

    class Meta:
        db_table = "plans"

    def __str__(self):
        return f"{self.code} - {self.nom}"


class PaiementAbonnement(models.Model):
    METHODES = [
        ("mtn", "MTN Mobile Money"),
        ("wave", "Wave"),
        ("orange", "Orange Money"),
        ("moov", "Moov Money"),
        ("visa", "Visa / Mastercard"),
        ("autre", "Autre"),
    ]
    STATUTS = [
        ("en_attente", "En attente"),
        ("paye", "Payé"),
        ("echoue", "Échoué"),
        ("annule", "Annulé"),
    ]

    reference = models.CharField(max_length=36, unique=True, editable=False)
    entreprise = models.ForeignKey(
        "entreprises.Entreprise",
        on_delete=models.CASCADE,
        related_name="paiements_abonnement",
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="paiements_abonnement",
    )
    methode = models.CharField(max_length=12, choices=METHODES)
    telephone = models.CharField(max_length=30, blank=True)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    devise = models.CharField(max_length=3)
    statut = models.CharField(max_length=10, choices=STATUTS, default="en_attente")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "paiements_abonnement"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"PAY-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)
