from django.db import migrations
from django.utils import timezone


def generate_invoices(apps, schema_editor):
    Facture = apps.get_model("facture", "Facture")
    Passage = apps.get_model("passage", "Passage")
    for passage in Passage.objects.filter(deleted_at__isnull=True).select_related("type_lavage", "vehicule").iterator():
        statut = "annule" if passage.statut == "annule" else passage.statut_reglement
        emission = timezone.localtime(passage.date_heure_debut).date()
        Facture.objects.get_or_create(
            passage_id=passage.pk,
            defaults={
                "entreprise_id": passage.entreprise_id,
                "client_id": passage.client_id,
                "numero": f"FAC-PASS-{passage.entreprise_id}-{passage.pk}",
                "objet": f"{passage.type_lavage.libelle} - {passage.vehicule.immatriculation}",
                "date_emission": emission,
                "montant_ht": passage.montant_total,
                "montant_total": passage.montant_total,
                "montant_paye": passage.montant_paye,
                "statut": statut,
                "created_by_id": passage.created_by_id or passage.user_id,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("facture", "0001_initial")]
    operations = [migrations.RunPython(generate_invoices, migrations.RunPython.noop)]
