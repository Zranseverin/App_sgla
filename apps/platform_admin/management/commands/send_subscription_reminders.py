from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from apps.entreprises.models import Entreprise
from apps.platform_admin.services import send_expiration_reminder


class Command(BaseCommand):
    help = "Envoie un rappel aux accès qui expirent dans les 3 prochains jours."

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-url",
            default=settings.PUBLIC_BASE_URL,
            help="URL publique de CleanGo utilisée dans les emails.",
        )

    def handle(self, *args, **options):
        today = timezone.localdate()
        target_date = today + timedelta(days=3)
        companies = Entreprise.objects.filter(
            Q(statut_abonnement="essai", date_fin_essai__range=(today, target_date))
            | Q(statut_abonnement="actif", date_fin_abonnement__range=(today, target_date))
        ).select_related("plan")
        sent = 0
        errors = 0
        for company in companies:
            end_date = (
                company.date_fin_essai
                if company.statut_abonnement == "essai"
                else company.date_fin_abonnement
            )
            try:
                if send_expiration_reminder(company, end_date, options["base_url"]):
                    sent += 1
            except Exception as exc:
                errors += 1
                self.stderr.write(f"{company.raison_sociale}: {exc}")
        self.stdout.write(self.style.SUCCESS(
            f"Rappels terminés : {sent} envoyé(s), {errors} erreur(s)."
        ))
