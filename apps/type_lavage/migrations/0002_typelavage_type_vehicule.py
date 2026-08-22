from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("type_lavage", "0001_initial")]

    operations = [
        migrations.AlterModelOptions(
            name="typelavage",
            options={"ordering": ["type_vehicule", "libelle"]},
        ),
        migrations.AddField(
            model_name="typelavage",
            name="type_vehicule",
            field=models.CharField(
                choices=[
                    ("tous", "Tous véhicules"),
                    ("moto", "Moto"),
                    ("tricycle", "Tricycle"),
                    ("voiture", "Voiture"),
                    ("suv_4x4", "SUV / 4x4"),
                    ("camionnette", "Camionnette"),
                    ("camion", "Camion"),
                    ("bus", "Bus / Minibus"),
                    ("autre", "Autre"),
                ],
                default="tous",
                max_length=20,
            ),
        ),
    ]
