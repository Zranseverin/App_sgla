from django.db import models

from apps.entreprises.models import Entreprise
class Role(models.Model):
    entreprise = models.ForeignKey(
        Entreprise,
        on_delete=models.CASCADE,
        db_column="entreprise_id",
        null=True,
        blank=True,
        related_name="roles",
    )
    code = models.CharField(max_length=40)
    libelle = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "roles"
        constraints = [
            models.UniqueConstraint(
                fields=["entreprise", "code"],
                name="uq_role_par_entreprise",
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.libelle}"
