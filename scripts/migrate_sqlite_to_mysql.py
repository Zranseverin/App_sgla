"""Importe les données métier de db.sqlite3 vers la base MySQL configurée."""

import os
import sqlite3
import sys
from pathlib import Path

import django

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import transaction

from apps.authentication.models import User
from apps.entreprises.models import Entreprise
from apps.plan.models import Plan
from apps.roles.models import Role


def run():
    source = sqlite3.connect("db.sqlite3")
    source.row_factory = sqlite3.Row

    with transaction.atomic():
        plan_map = {
            row["id"]: Plan.objects.get(code=row["code"])
            for row in source.execute("SELECT id, code FROM plans")
        }

        entreprise_map = {}
        for row in source.execute("SELECT * FROM entreprises"):
            entreprise = Entreprise.objects.filter(
                email_contact__iexact=row["email_contact"],
                raison_sociale=row["raison_sociale"],
            ).first()
            if entreprise is None:
                entreprise = Entreprise.objects.create(
                    raison_sociale=row["raison_sociale"],
                    logo_url=row["logo_url"],
                    couleur_principale=row["couleur_principale"],
                    devise=row["devise"],
                    langue=row["langue"],
                    fuseau_horaire=row["fuseau_horaire"],
                    statut_abonnement=row["statut_abonnement"],
                    date_debut_essai=row["date_debut_essai"],
                    date_fin_essai=row["date_fin_essai"],
                    email_contact=row["email_contact"],
                    telephone_contact=row["telephone_contact"],
                    plan=plan_map[row["plan_id"]],
                )
            entreprise_map[row["id"]] = entreprise

        role_map = {}
        for row in source.execute("SELECT * FROM roles"):
            entreprise = (
                entreprise_map[row["entreprise_id"]]
                if row["entreprise_id"] is not None
                else None
            )
            role, _ = Role.objects.get_or_create(
                entreprise=entreprise,
                code=row["code"],
                defaults={"libelle": row["libelle"]},
            )
            role_map[row["id"]] = role

        user_map = {}
        source_users = list(source.execute('SELECT * FROM "user"'))
        for row in source_users:
            user = User.objects.filter(email__iexact=row["email"]).first()
            if user is None:
                user = User.objects.create(
                    nom=row["nom"],
                    email=row["email"],
                    password=row["password"],
                    statut=row["statut"],
                    entreprise=entreprise_map[row["entreprise_id"]],
                    role=role_map[row["role_id"]],
                )
            user_map[row["id"]] = user

        for row in source_users:
            if row["invite_par_id"] is not None:
                user = user_map[row["id"]]
                user.invite_par = user_map[row["invite_par_id"]]
                user.save(update_fields=["invite_par"])

    source.close()
    print(
        {
            "plans": Plan.objects.count(),
            "entreprises": Entreprise.objects.count(),
            "roles": Role.objects.count(),
            "users": User.objects.count(),
        }
    )


if __name__ == "__main__":
    run()
