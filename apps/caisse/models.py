from django.core.validators import MinValueValidator
from django.db import models


class MouvementCaisse(models.Model):
    TYPES = [("entree", "Entrée"), ("sortie", "Sortie")]
    MODES = [("especes", "Espèces"), ("wave", "Wave"), ("orange", "Orange Money"), ("mtn", "MTN Mobile Money"), ("moov", "Moov Money"), ("carte", "Carte bancaire"), ("virement", "Virement"), ("forfait", "Forfait"), ("autre", "Autre")]
    STATUTS_PAIEMENT = [("paye", "Payé"), ("partiel", "Partiel"), ("non_paye", "Non payé"), ("annule", "Annulé")]

    entreprise = models.ForeignKey("entreprises.Entreprise", on_delete=models.CASCADE, related_name="mouvements_caisse")
    type_mouvement = models.CharField(max_length=10, choices=TYPES)
    montant = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    motif = models.CharField(max_length=180)
    reference = models.CharField(max_length=50, null=True, blank=True)
    mode_reglement = models.CharField(max_length=20, choices=MODES, default="especes")
    date_mouvement = models.DateTimeField()
    notes = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, related_name="mouvements_caisse_crees")
    passage = models.OneToOneField("passage.Passage", on_delete=models.CASCADE, null=True, blank=True, related_name="mouvement_caisse")
    statut_paiement = models.CharField(max_length=12, choices=STATUTS_PAIEMENT, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mouvement_caisse"
        ordering = ["-date_mouvement", "-pk"]

    def __str__(self):
        return f"{self.get_type_mouvement_display()} - {self.montant}"
