from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("entreprises", "0005_entreprise_taux_commission_laveur")]
    operations = [
        migrations.AddField(model_name="entreprise", name="adresse", field=models.CharField(blank=True, max_length=255, null=True)),
        migrations.AddField(model_name="entreprise", name="commune", field=models.CharField(blank=True, max_length=100, null=True)),
        migrations.AddField(model_name="entreprise", name="latitude", field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField(model_name="entreprise", name="longitude", field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
    ]
