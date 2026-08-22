from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.authentication.models import User
from apps.client.models import Client
from apps.employe.models import Employe
from apps.passage.models import Passage
from apps.type_lavage.models import TypeLavage
from apps.vehicule.models import Vehicule


def index(request):
    """Tableau de bord opérationnel de l'entreprise connectée."""
    user = User.objects.select_related("entreprise__plan", "role").filter(
        pk=request.session.get("utilisateur_id"), statut="actif",
    ).first()
    if user is None:
        messages.info(request, "Connectez-vous pour accéder au tableau de bord.")
        return redirect("authentication:connexion")

    entreprise = user.entreprise
    today = timezone.localdate()
    month_start = today.replace(day=1)
    next_month_start = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    passages = Passage.objects.filter(
        entreprise=entreprise, deleted_at__isnull=True,
    )
    month_passages = passages.filter(
        date_heure_debut__date__gte=month_start,
        date_heure_debut__date__lt=next_month_start,
    )
    valid_month_passages = month_passages.exclude(statut="annule")
    revenue = valid_month_passages.aggregate(value=Sum("montant_paye"))["value"] or Decimal("0")
    commissions = valid_month_passages.aggregate(value=Sum("commission_employe"))["value"] or Decimal("0")
    total_month = month_passages.count()
    completed = month_passages.filter(statut="termine").count()

    jours_restants = max((entreprise.date_fin_essai - today).days, 0) if entreprise.date_fin_essai else 0
    stats = {
        "jours_restants": jours_restants,
        "passages_today": passages.filter(date_heure_debut__date=today).count(),
        "passages_month": total_month,
        "revenue_month": revenue,
        "commissions_month": commissions,
        "unpaid": passages.filter(statut_reglement__in=("non_paye", "partiel")).exclude(statut="annule").count(),
        "clients": Client.objects.filter(entreprise=entreprise, deleted_at__isnull=True).count(),
        "vehicles": Vehicule.objects.filter(entreprise=entreprise, deleted_at__isnull=True).count(),
        "employees": Employe.objects.filter(entreprise=entreprise, statut="actif").count(),
        "wash_types": TypeLavage.objects.filter(entreprise=entreprise, actif=True, deleted_at__isnull=True).count(),
        "completion_rate": round(completed * 100 / total_month) if total_month else 0,
        "waiting_month": month_passages.filter(statut="en_attente").count(),
        "in_progress_month": month_passages.filter(statut="en_cours").count(),
        "completed_month": completed,
    }

    status_definitions = (
        ("en_attente", "En attente", "orange"),
        ("en_cours", "En cours", "blue"),
        ("termine", "Terminés", "green"),
        ("annule", "Annulés", "red"),
    )
    status_breakdown = []
    for code, label, color in status_definitions:
        count = month_passages.filter(statut=code).count()
        status_breakdown.append({
            "code": code, "label": label, "color": color, "count": count,
            "percent": round(count * 100 / total_month) if total_month else 0,
        })

    daily_data = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        day_passages = passages.filter(date_heure_debut__date=day).exclude(statut="annule")
        daily_data.append({
            "label": day.strftime("%d/%m"),
            "count": day_passages.count(),
            "revenue": day_passages.aggregate(value=Sum("montant_paye"))["value"] or Decimal("0"),
        })
    max_daily = max((item["count"] for item in daily_data), default=0)
    for item in daily_data:
        item["height"] = max(round(item["count"] * 100 / max_daily), 5) if max_daily else 5

    recent_passages = passages.select_related(
        "client", "vehicule", "type_lavage", "employe_realisateur",
    )[:8]
    popular_washes = TypeLavage.objects.filter(
        entreprise=entreprise, actif=True, deleted_at__isnull=True,
    ).annotate(
        passages_count=Count("passages", filter=Q(passages__date_heure_debut__date__gte=month_start, passages__deleted_at__isnull=True)),
        revenue=Sum("passages__montant_paye", filter=Q(passages__date_heure_debut__date__gte=month_start, passages__deleted_at__isnull=True) & ~Q(passages__statut="annule")),
    ).order_by("-passages_count", "libelle")[:5]

    return render(request, "dashboard/index.html", {
        "user": user, "entreprise": entreprise, "plan": entreprise.plan,
        "stats": stats, "today": today, "month_start": month_start,
        "status_breakdown": status_breakdown, "daily_data": daily_data,
        "recent_passages": recent_passages, "popular_washes": popular_washes,
        "user_initials": "".join(part[0].upper() for part in user.nom.split()[:2] if part),
    })


def reporting(request):
    """Reporting filtrable construit directement depuis les passages en base."""
    user = User.objects.select_related("entreprise__plan", "role").filter(
        pk=request.session.get("utilisateur_id"), statut="actif",
    ).first()
    if user is None:
        messages.info(request, "Connectez-vous pour accéder au reporting.")
        return redirect("authentication:connexion")

    entreprise = user.entreprise
    today = timezone.localdate()
    default_start = today.replace(day=1)

    def parse_date(value, fallback):
        try:
            return timezone.datetime.strptime(value, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return fallback

    date_start = parse_date(request.GET.get("debut"), default_start)
    date_end = parse_date(request.GET.get("fin"), today)
    if date_start > date_end:
        date_start, date_end = date_end, date_start

    query = request.GET.get("q", "").strip()
    selected_status = request.GET.get("statut", "").strip()
    passages = Passage.objects.filter(
        entreprise=entreprise,
        deleted_at__isnull=True,
        date_heure_debut__date__range=(date_start, date_end),
    ).select_related("client", "vehicule", "type_lavage", "employe_realisateur")
    if query:
        passages = passages.filter(
            Q(client__nom_complet__icontains=query)
            | Q(vehicule__immatriculation__icontains=query)
            | Q(type_lavage__libelle__icontains=query)
        )
    if selected_status in dict(Passage.STATUTS):
        passages = passages.filter(statut=selected_status)

    totals = passages.exclude(statut="annule").aggregate(
        revenue=Sum("montant_paye"),
        outstanding=Sum("montant_restant"),
        commissions=Sum("commission_employe"),
    )
    total_count = passages.count()
    completed_count = passages.filter(statut="termine").count()
    report_stats = {
        "total": total_count,
        "completed": completed_count,
        "completion_rate": round(completed_count * 100 / total_count) if total_count else 0,
        "revenue": totals["revenue"] or Decimal("0"),
        "outstanding": totals["outstanding"] or Decimal("0"),
        "commissions": totals["commissions"] or Decimal("0"),
    }

    status_definitions = (
        ("en_attente", "En attente", "orange"),
        ("en_cours", "En cours", "blue"),
        ("termine", "Terminés", "green"),
        ("annule", "Annulés", "red"),
    )
    status_breakdown = []
    for code, label, color in status_definitions:
        count = passages.filter(statut=code).count()
        status_breakdown.append({
            "code": code, "label": label, "color": color, "count": count,
            "percent": round(count * 100 / total_count) if total_count else 0,
        })

    grouped_daily = {
        item["day"]: item
        for item in passages.exclude(statut="annule").annotate(
            day=TruncDate("date_heure_debut")
        ).values("day").annotate(
            count=Count("id"), revenue=Sum("montant_paye"),
        ).order_by("day")
    }
    daily_data = []
    cursor = date_start
    while cursor <= date_end:
        item = grouped_daily.get(cursor, {})
        daily_data.append({
            "label": cursor.strftime("%d/%m"),
            "count": item.get("count", 0),
            "revenue": float(item.get("revenue") or 0),
        })
        cursor += timedelta(days=1)

    popular_washes = TypeLavage.objects.filter(
        entreprise=entreprise, deleted_at__isnull=True,
    ).annotate(
        passages_count=Count("passages", filter=Q(passages__in=passages)),
        revenue=Sum(
            "passages__montant_paye",
            filter=Q(passages__in=passages) & ~Q(passages__statut="annule"),
        ),
    ).filter(passages_count__gt=0).order_by("-passages_count", "libelle")[:10]

    laveur_reports_by_id = {}
    for passage in passages.order_by("employe_realisateur__nom", "-date_heure_debut"):
        laveur = passage.employe_realisateur
        report = laveur_reports_by_id.setdefault(laveur.pk, {
            "laveur": laveur,
            "passages": [],
            "total_prestations": Decimal("0"),
            "total_encaisse": Decimal("0"),
            "total_commissions": Decimal("0"),
        })
        report["passages"].append(passage)
        if passage.statut != "annule":
            report["total_prestations"] += passage.montant_total or Decimal("0")
            report["total_encaisse"] += passage.montant_paye or Decimal("0")
            report["total_commissions"] += passage.commission_employe or Decimal("0")
    laveur_reports = list(laveur_reports_by_id.values())

    jours_restants = max((entreprise.date_fin_essai - today).days, 0) if entreprise.date_fin_essai else 0
    return render(request, "dashboard/reporting.html", {
        "user": user, "entreprise": entreprise, "plan": entreprise.plan,
        "stats": {"jours_restants": jours_restants},
        "user_initials": "".join(part[0].upper() for part in user.nom.split()[:2] if part),
        "passages": passages[:100],
        "report_stats": report_stats,
        "daily_data": daily_data,
        "status_breakdown": status_breakdown,
        "popular_washes": popular_washes,
        "laveur_reports": laveur_reports,
        "date_start": date_start,
        "date_end": date_end,
        "query": query,
        "selected_status": selected_status,
        "status_choices": Passage.STATUTS,
    })
