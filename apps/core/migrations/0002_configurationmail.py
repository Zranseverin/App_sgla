import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_civilite"),
        ("entreprises", "0004_entreprise_image_uploads"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConfigurationMail",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nom_expediteur", models.CharField(max_length=120)),
                ("email_expediteur", models.EmailField(max_length=150)),
                ("serveur_smtp", models.CharField(default="smtp.gmail.com", max_length=150)),
                ("port_smtp", models.PositiveIntegerField(default=465)),
                ("utilisateur_smtp", models.CharField(max_length=150)),
                ("mot_de_passe_chiffre", models.TextField(blank=True)),
                ("utiliser_tls", models.BooleanField(default=False)),
                ("utiliser_ssl", models.BooleanField(default=True)),
                ("actif", models.BooleanField(default=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("entreprise", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="configuration_mail", to="entreprises.entreprise")),
            ],
            options={"db_table": "configurations_mail"},
        ),
    ]
