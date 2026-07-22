from django.db import migrations


def import_passage_payments(apps, schema_editor):
    Passage = apps.get_model("passage", "Passage")
    Mouvement = apps.get_model("caisse", "MouvementCaisse")
    passages = Passage.objects.filter(
        montant_paye__gt=0,
        deleted_at__isnull=True,
    ).exclude(statut="annule")
    for passage in passages.iterator():
        Mouvement.objects.update_or_create(
            passage_id=passage.pk,
            defaults={
                "entreprise_id": passage.entreprise_id,
                "type_mouvement": "entree",
                "montant": passage.montant_paye,
                "motif": f"Paiement du passage #{passage.pk}",
                "reference": f"PASS-{passage.pk}",
                "mode_reglement": passage.mode_reglement,
                "date_mouvement": passage.date_heure_debut,
                "created_by_id": passage.caissier_id,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("caisse", "0002_mouvementcaisse_passage_and_more")]
    operations = [migrations.RunPython(import_passage_payments, migrations.RunPython.noop)]
