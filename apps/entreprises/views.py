from math import cos, sin
import json
import secrets

from django.db.models import Count, Prefetch, Q
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Entreprise, VisitorEvent
from apps.type_lavage.models import TypeLavage


def public_directory(request):
    query = request.GET.get("q", "").strip()
    entreprises = Entreprise.objects.filter(
        statut_abonnement__in=("actif", "essai"),
    ).annotate(
        services_count=Count("types_lavage", filter=Q(types_lavage__actif=True, types_lavage__deleted_at__isnull=True)),
    ).prefetch_related(Prefetch("types_lavage", queryset=TypeLavage.objects.filter(actif=True, deleted_at__isnull=True).order_by("type_vehicule", "libelle"), to_attr="public_services")).order_by("raison_sociale")
    if query:
        entreprises = entreprises.filter(
            Q(raison_sociale__icontains=query)
            | Q(slogan__icontains=query)
            | Q(email_contact__icontains=query)
            | Q(telephone_contact__icontains=query)
        )
    map_companies = []
    for index, company in enumerate(entreprises):
        location_configured = company.latitude is not None and company.longitude is not None
        angle = index * 2.399963229728653
        radius = 0.012 + (index % 4) * 0.006
        map_companies.append({
            "id": company.pk,
            "name": company.raison_sociale,
            "slogan": company.slogan or "Service professionnel de lavage automobile",
            "phone": company.telephone_contact or "",
            "email": company.email_contact,
            "address": company.adresse or "",
            "commune": company.commune or "",
            "lat": float(company.latitude) if location_configured else 5.36 + sin(angle) * radius,
            "lng": float(company.longitude) if location_configured else -4.0083 + cos(angle) * radius,
            "color": company.couleur_principale or "#0e7c86",
            "logo": company.logo_url.url if company.logo_url else "",
            "initials": company.raison_sociale[:2].upper(),
            "location_configured": location_configured,
            "currency": company.devise,
            "catalog": [{"name": service.libelle, "vehicle": service.get_type_vehicule_display(), "price": float(service.prix_unitaire), "duration": service.duree_estimee_min, "description": service.description or ""} for service in company.public_services],
        })
    return render(request, "entreprises/public_directory.html", {
        "entreprises": entreprises,
        "map_companies": map_companies,
        "query": query,
        "total_entreprises": entreprises.count(),
    })


def _client_ip(request):
    cloudflare_ip = request.META.get("HTTP_CF_CONNECTING_IP", "").strip()
    if cloudflare_ip:
        return cloudflare_ip
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")) or None


@csrf_exempt
@require_POST
def track_visitor_event(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "invalid_payload"}, status=400)
    valid_types = {value for value, _ in VisitorEvent.EVENT_TYPES}
    event_type = payload.get("event_type")
    if event_type not in valid_types:
        return JsonResponse({"ok": False, "error": "invalid_event"}, status=400)
    if not request.session.session_key:
        request.session.create()
    visitor_id = str(payload.get("visitor_id") or secrets.token_urlsafe(18))[:64]
    company_id = payload.get("company_id")
    company = Entreprise.objects.filter(pk=company_id).first() if company_id else None
    VisitorEvent.objects.create(
        event_type=event_type,
        visitor_id=visitor_id,
        session_key=request.session.session_key or "",
        ip_address=_client_ip(request),
        device_label=str(payload.get("device_label") or "")[:120],
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:2000],
        page_path=str(payload.get("page_path") or "")[:255],
        referrer=str(payload.get("referrer") or "")[:500],
        search_query=str(payload.get("search_query") or "")[:255],
        latitude=payload.get("latitude"),
        longitude=payload.get("longitude"),
        locality=str(payload.get("locality") or "")[:180],
        entreprise=company,
        metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
    )
    return JsonResponse({"ok": True, "visitor_id": visitor_id})
