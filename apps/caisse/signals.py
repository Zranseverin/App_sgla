from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.passage.models import Passage
from .models import MouvementCaisse


@receiver(post_save, sender=Passage)
def synchroniser_paiement_passage(sender, instance, **kwargs):
    """Un paiement de passage correspond à une unique entrée de caisse."""
    if instance.deleted_at:
        MouvementCaisse.objects.filter(passage=instance).delete()
        return
    statut = "annule" if instance.statut == "annule" else instance.statut_reglement
    montant = 0 if statut == "annule" else instance.montant_paye
    MouvementCaisse.objects.update_or_create(
        passage=instance,
        defaults={
            "entreprise": instance.entreprise,
            "type_mouvement": "entree",
            "montant": montant,
            "motif": f"Paiement du passage #{instance.pk}",
            "reference": f"PASS-{instance.pk}",
            "mode_reglement": instance.mode_reglement,
            "date_mouvement": instance.date_heure_debut,
            "created_by": instance.caissier,
            "statut_paiement": statut,
        },
    )
