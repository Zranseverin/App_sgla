from django.contrib import messages
from django.db.models import Q, Sum
from django.db import transaction
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.utils import timezone

from apps.authentication.models import User
from apps.vehicule.models import Vehicule
from apps.client.models import Client
from apps.type_lavage.models import TypeLavage
import secrets

from .forms import PassageForm
from .models import Passage


def _connected_user(request):
    return User.objects.select_related("entreprise__plan", "role").filter(
        pk=request.session.get("utilisateur_id"),
        statut="actif",
    ).first()


def _layout_context(user):
    entreprise = user.entreprise
    jours_restants = max((entreprise.date_fin_essai - timezone.localdate()).days, 0) if entreprise.date_fin_essai else 0
    return {
        "user": user, "entreprise": entreprise, "plan": entreprise.plan,
        "stats": {"jours_restants": jours_restants},
        "user_initials": "".join(part[0].upper() for part in user.nom.split()[:2] if part),
    }


def _uses_new_client(request):
    """Infer the mode from entered data, as the reference passage form does."""
    has_new_data = any(
        request.POST.get(field, "").strip()
        for field in (
            "new_client_nom_complet",
            "new_client_telephone",
            "new_client_adresse",
        )
    )
    return request.POST.get("client_mode") == "new" or has_new_data


def _uses_new_vehicle(request):
    return (
        request.POST.get("vehicule_mode") == "new"
        or bool(request.POST.get("new_vehicle_immatriculation", "").strip())
    )


def _resolve_client_and_vehicle(request, user):
    entreprise = user.entreprise
    if _uses_new_client(request):
        nom = request.POST.get("new_client_nom_complet", "").strip()
        telephone = request.POST.get("new_client_telephone", "").strip()
        adresse = request.POST.get("new_client_adresse", "").strip()
        email = request.POST.get("new_client_email", "").strip() or None
        if not nom or not telephone or not adresse:
            raise ValidationError("Nom complet, téléphone et adresse sont obligatoires pour le nouveau client.")
        if Client.objects.filter(entreprise=entreprise, telephone=telephone, deleted_at__isnull=True).exists():
            raise ValidationError("Un client existe déjà avec ce numéro de téléphone.")
        client = Client.objects.create(
            code=f"CLI-{secrets.token_hex(3).upper()}",
            nom_complet=nom,
            telephone=telephone,
            adresse=adresse,
            email=email,
            entreprise=entreprise,
            user=user,
            created_by=user,
            updated_by=user,
        )
    else:
        client = Client.objects.filter(
            pk=request.POST.get("client"),
            entreprise=entreprise,
            deleted_at__isnull=True,
        ).first()
        if client is None:
            raise ValidationError("Sélectionnez un client existant.")

    if _uses_new_vehicle(request):
        immatriculation = request.POST.get("new_vehicle_immatriculation", "").strip().upper()
        if not immatriculation:
            raise ValidationError("L’immatriculation est obligatoire pour le nouveau véhicule.")
        if Vehicule.objects.filter(entreprise=entreprise, immatriculation__iexact=immatriculation, deleted_at__isnull=True).exists():
            raise ValidationError("Un véhicule existe déjà avec cette immatriculation.")
        vehicle = Vehicule.objects.create(
            client=client,
            immatriculation=immatriculation,
            type_vehicule=request.POST.get("new_vehicle_type_vehicule", "").strip() or None,
            marque=request.POST.get("new_vehicle_marque", "").strip() or None,
            modele=request.POST.get("new_vehicle_modele", "").strip() or None,
            couleur=request.POST.get("new_vehicle_couleur", "").strip() or None,
            entreprise=entreprise,
            user=user,
            created_by=user,
            updated_by=user,
        )
    else:
        vehicle = Vehicule.objects.filter(
            pk=request.POST.get("vehicule"),
            client=client,
            entreprise=entreprise,
            deleted_at__isnull=True,
        ).first()
        if vehicle is None:
            raise ValidationError("Sélectionnez un véhicule appartenant au client.")
    return client, vehicle


def _add_resolution_error(form, error):
    """Expose client/vehicle validation errors in the passage form."""
    for message in error.messages:
        form.add_error(None, message)


def passage_list(request):
    user = _connected_user(request)
    if user is None:
        return redirect("authentication:connexion")
    passages = Passage.objects.filter(
        entreprise=user.entreprise,
        deleted_at__isnull=True,
    ).select_related("client", "vehicule", "type_lavage", "employe_realisateur")
    query = request.GET.get("q", "").strip()
    if query:
        passages = passages.filter(
            Q(client__nom_complet__icontains=query)
            | Q(vehicule__immatriculation__icontains=query)
            | Q(type_lavage__libelle__icontains=query)
        )
    total_amount = passages.aggregate(total=Sum("montant_total"))["total"] or 0
    context = _layout_context(user)
    context.update({
        "passages": passages,
        "total": passages.count(),
        "total_amount": total_amount,
        "query": query,
    })
    return render(request, "passage/index.html", context)


def passage_create(request):
    user = _connected_user(request)
    if user is None:
        return redirect("authentication:connexion")
    form = PassageForm(
        request.POST or None,
        entreprise=user.entreprise,
        initial={
            "date_heure_debut": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            "statut": "en_attente",
            "statut_reglement": "non_paye",
        },
    )
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                client, vehicle = _resolve_client_and_vehicle(request, user)
                passage = form.save(commit=False)
                passage.client = client
                passage.vehicule = vehicle
                passage.entreprise = user.entreprise
                passage.user = user
                passage.caissier = user
                passage.created_by = user
                passage.updated_by = user
                if passage.statut == "annule":
                    passage.annulateur = user
                    passage.date_annulation = passage.date_annulation or timezone.now()
                passage.save()
        except ValidationError as error:
            _add_resolution_error(form, error)
        else:
            messages.success(request, f"Le passage #{passage.pk} a été créé et sa facture a été générée.")
            return redirect("facture:detail", pk=passage.facture.pk)
    context = _layout_context(user)
    context.update({
        "form": form,
        "page_title": "Créer un passage",
        "clients": Client.objects.filter(entreprise=user.entreprise, deleted_at__isnull=True),
        "selected_client_id": request.POST.get("client", ""),
        "selected_vehicle_id": request.POST.get("vehicule", ""),
        "wash_prices": {
            str(item.pk): float(item.prix_unitaire)
            for item in TypeLavage.objects.filter(
                entreprise=user.entreprise,
                deleted_at__isnull=True,
                actif=True,
            )
        },
    })
    return render(request, "passage/form.html", context)


def passage_update(request, pk):
    user = _connected_user(request)
    if user is None:
        return redirect("authentication:connexion")
    passage = get_object_or_404(Passage, pk=pk, entreprise=user.entreprise, deleted_at__isnull=True)
    form = PassageForm(request.POST or None, instance=passage, entreprise=user.entreprise)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                client, vehicle = _resolve_client_and_vehicle(request, user)
                passage = form.save(commit=False)
                passage.client = client
                passage.vehicule = vehicle
                passage.updated_by = user
                if passage.statut == "annule":
                    passage.annulateur = user
                    passage.date_annulation = passage.date_annulation or timezone.now()
                passage.save()
        except ValidationError as error:
            _add_resolution_error(form, error)
        else:
            messages.success(request, "Le passage a été modifié.")
            return redirect("passage:index")
    context = _layout_context(user)
    context.update({
        "form": form,
        "page_title": f"Modifier le passage #{passage.pk}",
        "passage": passage,
        "clients": Client.objects.filter(entreprise=user.entreprise, deleted_at__isnull=True),
        "selected_client_id": request.POST.get("client", passage.client_id),
        "selected_vehicle_id": request.POST.get("vehicule", passage.vehicule_id),
        "wash_prices": {
            str(item.pk): float(item.prix_unitaire)
            for item in TypeLavage.objects.filter(
                entreprise=user.entreprise,
                deleted_at__isnull=True,
                actif=True,
            )
        },
    })
    return render(request, "passage/form.html", context)


def passage_delete(request, pk):
    user = _connected_user(request)
    if user is None:
        return redirect("authentication:connexion")
    passage = get_object_or_404(Passage, pk=pk, entreprise=user.entreprise, deleted_at__isnull=True)
    if request.method == "POST":
        passage.deleted_at = timezone.now()
        passage.deleted_by = user
        passage.save(update_fields=["deleted_at", "deleted_by", "updated_at"])
        messages.success(request, "Le passage a été supprimé.")
    return redirect("passage:index")


def passage_change_status(request, pk):
    user = _connected_user(request)
    if user is None:
        return redirect("authentication:connexion")
    passage = get_object_or_404(
        Passage,
        pk=pk,
        entreprise=user.entreprise,
        deleted_at__isnull=True,
    )
    if request.method != "POST":
        return redirect("passage:index")
    if passage.statut == "termine":
        messages.info(request, "Ce passage est déjà terminé et son statut ne peut plus être modifié.")
        return redirect("passage:index")

    transitions = {"en_attente": "en_cours", "en_cours": "termine"}
    nouveau_statut = transitions.get(passage.statut)
    if nouveau_statut is None:
        messages.error(request, "Ce passage ne peut pas changer de statut.")
        return redirect("passage:index")

    passage.statut = nouveau_statut
    passage.date_heure_fin = timezone.now() if nouveau_statut == "termine" else None
    passage.updated_by = user
    passage.save()
    messages.success(request, f"Le passage #{passage.pk} est maintenant {passage.get_statut_display().lower()}.")
    return redirect("passage:index")


def vehicles_by_client(request, client_id):
    user = _connected_user(request)
    if user is None:
        return JsonResponse({"detail": "Authentification requise."}, status=401)
    vehicles = Vehicule.objects.filter(
        entreprise=user.entreprise,
        client_id=client_id,
        client__entreprise=user.entreprise,
        client__deleted_at__isnull=True,
        deleted_at__isnull=True,
    ).order_by("immatriculation")
    return JsonResponse({
        "vehicules": [
            {
                "id": vehicle.pk,
                "label": " ".join(filter(None, [
                    vehicle.immatriculation,
                    "—",
                    vehicle.marque,
                    vehicle.modele,
                ])),
            }
            for vehicle in vehicles
        ],
    })
