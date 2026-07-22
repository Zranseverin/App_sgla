from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("entreprises", "0002_alter_entreprise_plan"),
    ]

    operations = [
        migrations.AddField(
            model_name="entreprise",
            name="favicon_url",
            field=models.URLField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="entreprise",
            name="slogan",
            field=models.CharField(blank=True, max_length=180, null=True),
        ),
    ]
