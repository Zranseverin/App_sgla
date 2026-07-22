from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations


def recalculate_commissions(apps, schema_editor):
    Passage = apps.get_model("passage", "Passage")
    for passage in Passage.objects.all().iterator():
        paid = passage.montant_paye or Decimal("0")
        commission = (paid * Decimal("0.20")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        Passage.objects.filter(pk=passage.pk).update(
            commission_employe=commission,
            net_station=paid - commission,
        )


class Migration(migrations.Migration):
    dependencies = [("passage", "0004_remove_passage_forfait_id")]
    operations = [migrations.RunPython(recalculate_commissions, migrations.RunPython.noop)]
