from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("entreprises", "0003_entreprise_branding"),
    ]

    operations = [
        migrations.AlterField(
            model_name="entreprise",
            name="logo_url",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="entreprises/logos/",
            ),
        ),
        migrations.AlterField(
            model_name="entreprise",
            name="favicon_url",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="entreprises/favicons/",
            ),
        ),
    ]
