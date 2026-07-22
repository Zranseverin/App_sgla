import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("authentication", "0002_user_photo"),
        ("core", "0002_configurationmail"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="adresse",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="civilite",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="utilisateurs", to="core.civilite"),
        ),
        migrations.AddField(
            model_name="user",
            name="matricule",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="telephone",
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(fields=("entreprise", "matricule"), name="uq_matricule_par_entreprise"),
        ),
    ]
