from django.core.validators import MinValueValidator
from django.db import models


class Employe(models.Model):
    STATUTS = [("actif", "Actif"), ("mission", "En mission"), ("conge", "En congé"), ("suspendu", "Suspendu"), ("inactif", "Inactif")]
    user = models.OneToOneField("authentication.User", on_delete=models.CASCADE, related_name="fiche_employe")
    entreprise = models.ForeignKey("entreprises.Entreprise", on_delete=models.CASCADE, related_name="employes")
    poste = models.CharField(max_length=100)
    date_naissance = models.DateField(null=True, blank=True)
    date_embauche = models.DateField()
    numero_piece_identite = models.CharField(max_length=50, null=True, blank=True)
    numero_cnps = models.CharField(max_length=50, null=True, blank=True)
    salaire_brut = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    categorie_permis = models.CharField(max_length=30, null=True, blank=True)
    numero_permis = models.CharField(max_length=50, null=True, blank=True)
    expiration_permis = models.DateField(null=True, blank=True)
    banque = models.CharField(max_length=100, null=True, blank=True)
    iban = models.CharField(max_length=50, null=True, blank=True)
    statut = models.CharField(max_length=10, choices=STATUTS, default="actif")
    created_by = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="fiches_employes_creees")
    updated_by = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="fiches_employes_modifiees")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "employe"
        ordering = ["user__nom"]
        constraints = [models.UniqueConstraint(fields=["entreprise", "numero_cnps"], name="uq_cnps_par_entreprise")]

    def __str__(self):
        return f"{self.user.nom} - {self.poste}"

    @property
    def initiales(self):
        return "".join(part[0].upper() for part in self.user.nom.split()[:2] if part)
