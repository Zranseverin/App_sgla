from django.db import models


class TypeLavage(models.Model):
    libelle = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    duree_estimee_min = models.IntegerField(null=True, blank=True)
    actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="types_lavage_crees",
    )
    deleted_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="types_lavage_supprimes",
    )
    entreprise = models.ForeignKey(
        "entreprises.Entreprise",
        on_delete=models.CASCADE,
        related_name="types_lavage",
    )
    updated_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="types_lavage_modifies",
    )
    user = models.ForeignKey(
        "authentication.User",
        on_delete=models.PROTECT,
        related_name="types_lavage",
    )

    class Meta:
        db_table = "type_lavage"
        ordering = ["libelle"]

    def __str__(self):
        return self.libelle
