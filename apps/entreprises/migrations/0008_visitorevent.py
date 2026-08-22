from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("entreprises", "0007_entreprise_date_debut_abonnement_and_more")]
    operations = [
        migrations.CreateModel(
            name="VisitorEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(choices=[("page_view", "Consultation de page"), ("search", "Recherche"), ("geolocation_request", "Clic sur Me localiser"), ("geolocation_success", "Localisation autorisée"), ("company_view", "Entreprise consultée"), ("catalog_view", "Catalogue consulté"), ("route_request", "Itinéraire demandé")], max_length=24)),
                ("visitor_id", models.CharField(db_index=True, max_length=64)),
                ("session_key", models.CharField(blank=True, max_length=40)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("device_label", models.CharField(blank=True, max_length=120)),
                ("user_agent", models.TextField(blank=True)),
                ("page_path", models.CharField(blank=True, max_length=255)),
                ("referrer", models.URLField(blank=True, max_length=500)),
                ("search_query", models.CharField(blank=True, max_length=255)),
                ("latitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("longitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("locality", models.CharField(blank=True, max_length=180)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("entreprise", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="visitor_events", to="entreprises.entreprise")),
            ],
            options={"db_table": "visitor_events", "ordering": ["-created_at"]},
        ),
    ]
