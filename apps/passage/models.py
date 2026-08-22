from decimal import Decimal, ROUND_HALF_UP

from django.db import models


class Passage(models.Model):
    MODES_REGLEMENT = [
        ("especes", "Espèces"),
        ("wave", "Wave"),
        ("orange", "Orange Money"),
        ("mtn", "MTN Mobile Money"),
        ("moov", "Moov Money"),
        ("carte", "Carte bancaire"),
    ]
    STATUTS = [
        ("en_attente", "En attente"),
        ("en_cours", "En cours"),
        ("termine", "Terminé"),
        ("annule", "Annulé"),
    ]
    STATUTS_REGLEMENT = [
        ("non_paye", "Non payé"),
        ("partiel", "Partiel"),
        ("paye", "Payé"),
    ]

    date_heure_debut = models.DateTimeField()
    date_heure_fin = models.DateTimeField(null=True, blank=True)
    date_annulation = models.DateTimeField(null=True, blank=True)
    montant_paye = models.DecimalField(max_digits=10, decimal_places=2)
    mode_reglement = models.CharField(max_length=15, choices=MODES_REGLEMENT)
    statut = models.CharField(max_length=10, choices=STATUTS)
    motif_annulation = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    annulateur = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="passages_annules")
    caissier = models.ForeignKey("authentication.User", on_delete=models.PROTECT, related_name="passages_encaisses")
    client = models.ForeignKey("client.Client", on_delete=models.PROTECT, related_name="passages")
    created_by = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="passages_crees")
    deleted_by = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="passages_supprimes")
    employe_realisateur = models.ForeignKey("authentication.User", on_delete=models.PROTECT, related_name="passages_realises")
    entreprise = models.ForeignKey("entreprises.Entreprise", on_delete=models.CASCADE, related_name="passages")
    piste_id = models.PositiveBigIntegerField(null=True, blank=True)
    type_lavage = models.ForeignKey("type_lavage.TypeLavage", on_delete=models.PROTECT, related_name="passages")
    updated_by = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="passages_modifies")
    user = models.ForeignKey("authentication.User", on_delete=models.PROTECT, related_name="passages")
    vehicule = models.ForeignKey("vehicule.Vehicule", on_delete=models.PROTECT, related_name="passages")
    commission_employe = models.DecimalField(max_digits=10, decimal_places=2)
    montant_partiel_verse = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    montant_restant = models.DecimalField(max_digits=10, decimal_places=2)
    montant_total = models.DecimalField(max_digits=10, decimal_places=2)
    net_station = models.DecimalField(max_digits=10, decimal_places=2)
    statut_reglement = models.CharField(max_length=20, choices=STATUTS_REGLEMENT)

    class Meta:
        db_table = "passage"
        ordering = ["-date_heure_debut"]

    def __str__(self):
        return f"Passage #{self.pk} - {self.vehicule}"

    def save(self, *args, **kwargs):
        """Recalcule toujours les montants financiers avant l'enregistrement."""
        total = self.montant_total or Decimal("0")
        paid = self.montant_paye or Decimal("0")
        paid = min(max(paid, Decimal("0")), total)
        rate_percent = getattr(self.entreprise, "taux_commission_laveur", Decimal("20"))
        commission = (paid * rate_percent / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        self.montant_total = total
        self.montant_paye = paid
        self.montant_partiel_verse = paid
        self.montant_restant = total - paid
        self.commission_employe = commission
        self.net_station = paid - commission
        super().save(*args, **kwargs)
