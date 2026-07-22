import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("entreprises", "0004_entreprise_image_uploads"),
    ]

    operations = [
        migrations.CreateModel(
            name="Civilite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=20)),
                ("libelle", models.CharField(max_length=80)),
                ("actif", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("entreprise", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="civilites", to="entreprises.entreprise")),
            ],
            options={
                "db_table": "civilites",
                "constraints": [
                    models.UniqueConstraint(fields=("entreprise", "code"), name="uq_civilite_par_entreprise"),
                ],
            },
        ),
    ]
