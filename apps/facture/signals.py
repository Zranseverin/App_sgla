from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.passage.models import Passage
from .models import Facture


@receiver(post_save, sender=Passage)
def synchroniser_facture_du_passage(sender, instance, **kwargs):
    statut = "annule" if instance.statut == "annule" else instance.statut_reglement
    facture, created = Facture.objects.get_or_create(
        passage=instance,
        defaults={
            "entreprise": instance.entreprise,
            "client": instance.client,
            "numero": f"FAC-PASS-{instance.entreprise_id}-{instance.pk}",
            "objet": f"{instance.type_lavage.libelle} - {instance.vehicule.immatriculation}",
            "date_emission": timezone.localdate(instance.date_heure_debut),
            "montant_ht": instance.montant_total,
            "montant_paye": instance.montant_paye,
            "statut": statut,
            "created_by": instance.created_by or instance.user,
        },
    )
    if created:
        return
    facture.client = instance.client
    facture.objet = f"{instance.type_lavage.libelle} - {instance.vehicule.immatriculation}"
    facture.montant_ht = instance.montant_total
    facture.montant_paye = instance.montant_paye
    if instance.statut == "annule":
        facture.statut = "annule"
    elif facture.statut == "annule":
        facture.statut = "non_paye"
    facture.save()
