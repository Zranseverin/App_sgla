import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("entreprises", "0004_entreprise_image_uploads"),
        ("plan", "0002_seed_subscription_plans"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaiementAbonnement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference", models.CharField(editable=False, max_length=36, unique=True)),
                ("methode", models.CharField(choices=[("mtn", "MTN Mobile Money"), ("wave", "Wave"), ("orange", "Orange Money"), ("moov", "Moov Money"), ("visa", "Visa / Mastercard"), ("autre", "Autre")], max_length=12)),
                ("telephone", models.CharField(blank=True, max_length=30)),
                ("montant", models.DecimalField(decimal_places=2, max_digits=10)),
                ("devise", models.CharField(max_length=3)),
                ("statut", models.CharField(choices=[("en_attente", "En attente"), ("paye", "Payé"), ("echoue", "Échoué"), ("annule", "Annulé")], default="en_attente", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("entreprise", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="paiements_abonnement", to="entreprises.entreprise")),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="paiements_abonnement", to="plan.plan")),
            ],
            options={"db_table": "paiements_abonnement", "ordering": ["-created_at"]},
        ),
    ]
