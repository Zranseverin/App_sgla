from django.apps import AppConfig


class CaisseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.caisse"
    verbose_name = "Caisse"

    def ready(self):
        from . import signals  # noqa: F401
