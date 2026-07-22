from django.db import models


class Vehicule(models.Model):
    immatriculation = models.CharField(max_length=20)
    marque = models.CharField(max_length=50, null=True, blank=True)
    modele = models.CharField(max_length=50, null=True, blank=True)
    couleur = models.CharField(max_length=30, null=True, blank=True)
    type_vehicule = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    client = models.ForeignKey(
        "client.Client",
        on_delete=models.PROTECT,
        related_name="vehicules",
    )
    created_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicules_crees",
    )
    deleted_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicules_supprimes",
    )
    entreprise = models.ForeignKey(
        "entreprises.Entreprise",
        on_delete=models.CASCADE,
        related_name="vehicules",
    )
    updated_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicules_modifies",
    )
    user = models.ForeignKey(
        "authentication.User",
        on_delete=models.PROTECT,
        related_name="vehicules",
    )

    class Meta:
        db_table = "vehicule"
        ordering = ["immatriculation"]

    def __str__(self):
        return self.immatriculation
