from decimal import Decimal
from django.db import models


class Facture(models.Model):
    STATUTS = [("non_paye", "Non payée"), ("partiel", "Partiellement payée"), ("paye", "Payée"), ("annule", "Annulée")]
    entreprise = models.ForeignKey("entreprises.Entreprise", on_delete=models.CASCADE, related_name="factures")
    client = models.ForeignKey("client.Client", on_delete=models.PROTECT, related_name="factures")
    passage = models.OneToOneField("passage.Passage", on_delete=models.SET_NULL, null=True, blank=True, related_name="facture")
    numero = models.CharField(max_length=30)
    objet = models.CharField(max_length=180)
    date_emission = models.DateField()
    date_echeance = models.DateField(null=True, blank=True)
    montant_ht = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remise = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    taxe = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_paye = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    statut = models.CharField(max_length=12, choices=STATUTS, default="non_paye")
    notes = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, related_name="factures_creees")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "facture"
        ordering = ["-date_emission", "-pk"]
        constraints = [models.UniqueConstraint(fields=["entreprise", "numero"], name="uq_numero_facture_entreprise")]

    def save(self, *args, **kwargs):
        self.montant_ht = max(self.montant_ht or Decimal("0"), Decimal("0"))
        self.remise = min(max(self.remise or Decimal("0"), Decimal("0")), self.montant_ht)
        self.taxe = max(self.taxe or Decimal("0"), Decimal("0"))
        self.montant_total = self.montant_ht - self.remise + self.taxe
        self.montant_paye = min(max(self.montant_paye or Decimal("0"), Decimal("0")), self.montant_total)
        if self.statut != "annule":
            self.statut = "paye" if self.montant_total > 0 and self.montant_paye >= self.montant_total else ("partiel" if self.montant_paye > 0 else "non_paye")
        super().save(*args, **kwargs)

    @property
    def montant_restant(self):
        return self.montant_total - self.montant_paye

    def __str__(self):
        return self.numero
