from getpass import getpass

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.platform_admin.models import CleanGoAdmin


class Command(BaseCommand):
    help = "Crée ou met à jour un administrateur de la plateforme CleanGo."

    def add_arguments(self, parser):
        parser.add_argument("--name", default="Administrateur CleanGo")
        parser.add_argument("--email", required=True)
        parser.add_argument("--password")
        parser.add_argument("--telephone", default="")

    @transaction.atomic
    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        password = options.get("password") or getpass("Mot de passe de l’administrateur : ")
        if len(password) < 8:
            raise CommandError("Le mot de passe doit contenir au moins 8 caractères.")

        admin = CleanGoAdmin.objects.filter(email__iexact=email).first()
        created = admin is None
        if created:
            admin = CleanGoAdmin(email=email)
        admin.nom = options["name"]
        admin.telephone = options["telephone"]
        admin.statut = "actif"
        admin.set_password(password)
        admin.save()

        action = "créé" if created else "mis à jour"
        self.stdout.write(self.style.SUCCESS(
            f"Administrateur {action} : {email}. Connexion : /cleango-admin/connexion/"
        ))
