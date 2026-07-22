from django.apps import AppConfig


class FactureConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.facture"
    verbose_name = "Factures"

    def ready(self):
        from . import signals  # noqa: F401
