from decimal import Decimal

from django.db import migrations


PLANS = (
    {
        "code": "starter",
        "nom": "Starter",
        "description": "L'essentiel pour lancer et organiser une première activité.",
        "prix_mensuel": Decimal("15000.00"),
        "devise": "XOF",
        "max_centres": 1,
        "max_utilisateurs": 5,
        "quota_sms_mensuel": 100,
        "duree_essai_jours": 14,
        "actif": True,
    },
    {
        "code": "pro",
        "nom": "Pro",
        "description": "Des capacités étendues pour les entreprises en croissance.",
        "prix_mensuel": Decimal("35000.00"),
        "devise": "XOF",
        "max_centres": 5,
        "max_utilisateurs": 25,
        "quota_sms_mensuel": 500,
        "duree_essai_jours": 14,
        "actif": True,
    },
    {
        "code": "entreprise",
        "nom": "Entreprise",
        "description": "Une configuration sans limites pour les réseaux structurés.",
        "prix_mensuel": Decimal("75000.00"),
        "devise": "XOF",
        "max_centres": None,
        "max_utilisateurs": None,
        "quota_sms_mensuel": 2000,
        "duree_essai_jours": 30,
        "actif": True,
    },
)


def seed_plans(apps, schema_editor):
    Plan = apps.get_model("plan", "Plan")
    for data in PLANS:
        code = data["code"]
        defaults = {key: value for key, value in data.items() if key != "code"}
        Plan.objects.update_or_create(code=code, defaults=defaults)


def remove_plans(apps, schema_editor):
    Plan = apps.get_model("plan", "Plan")
    Plan.objects.filter(code__in=[plan["code"] for plan in PLANS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("plan", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_plans, remove_plans),
    ]
