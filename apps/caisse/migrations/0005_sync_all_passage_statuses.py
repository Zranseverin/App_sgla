from django.db import migrations


def sync_all_passages(apps, schema_editor):
    Passage = apps.get_model("passage", "Passage")
    Mouvement = apps.get_model("caisse", "MouvementCaisse")
    for passage in Passage.objects.filter(deleted_at__isnull=True).iterator():
        statut = "annule" if passage.statut == "annule" else passage.statut_reglement
        Mouvement.objects.update_or_create(
            passage_id=passage.pk,
            defaults={
                "entreprise_id": passage.entreprise_id,
                "type_mouvement": "entree",
                "montant": 0 if statut == "annule" else (passage.montant_paye or 0),
                "motif": f"Paiement du passage #{passage.pk}",
                "reference": f"PASS-{passage.pk}",
                "mode_reglement": passage.mode_reglement,
                "date_mouvement": passage.date_heure_debut,
                "created_by_id": passage.caissier_id,
                "statut_paiement": statut,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("caisse", "0004_mouvementcaisse_statut_paiement_and_more")]
    operations = [migrations.RunPython(sync_all_passages, migrations.RunPython.noop)]
