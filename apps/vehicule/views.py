from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.authentication.models import User

from .forms import VehiculeForm
from .models import Vehicule


def _connected_user(request):
    return User.objects.select_related("entreprise__plan", "role").filter(
        pk=request.session.get("utilisateur_id"),
        statut="actif",
    ).first()


def _layout_context(user):
    entreprise = user.entreprise
    jours_restants = (
        max((entreprise.date_fin_essai - timezone.localdate()).days, 0)
        if entreprise.date_fin_essai else 0
    )
    return {
        "user": user,
        "entreprise": entreprise,
        "plan": entreprise.plan,
        "stats": {"jours_restants": jours_restants},
        "user_initials": "".join(part[0].upper() for part in user.nom.split()[:2] if part),
    }


def vehicule_list(request):
    user = _connected_user(request)
    if user is None:
        return redirect("authentication:connexion")
    vehicules = Vehicule.objects.filter(
        entreprise=user.entreprise,
        deleted_at__isnull=True,
    ).select_related("client")
    query = request.GET.get("q", "").strip()
    if query:
        vehicules = vehicules.filter(
            Q(immatriculation__icontains=query)
            | Q(marque__icontains=query)
            | Q(modele__icontains=query)
            | Q(client__nom_complet__icontains=query)
        )
    context = _layout_context(user)
    context.update({"vehicules": vehicules, "total": vehicules.count(), "query": query})
    return render(request, "vehicule/index.html", context)


def vehicule_create(request):
    user = _connected_user(request)
    if user is None:
        return redirect("authentication:connexion")
    form = VehiculeForm(request.POST or None, entreprise=user.entreprise)
    if request.method == "POST" and form.is_valid():
        vehicule = form.save(commit=False)
        vehicule.entreprise = user.entreprise
        vehicule.user = user
        vehicule.created_by = user
        vehicule.updated_by = user
        vehicule.save()
        messages.success(request, f"Le véhicule {vehicule.immatriculation} a été créé.")
        return redirect("vehicule:index")
    context = _layout_context(user)
    context.update({"form": form, "page_title": "Créer un véhicule"})
    return render(request, "vehicule/form.html", context)


def vehicule_update(request, pk):
    user = _connected_user(request)
    if user is None:
        return redirect("authentication:connexion")
    vehicule = get_object_or_404(
        Vehicule,
        pk=pk,
        entreprise=user.entreprise,
        deleted_at__isnull=True,
    )
    form = VehiculeForm(request.POST or None, instance=vehicule, entreprise=user.entreprise)
    if request.method == "POST" and form.is_valid():
        vehicule = form.save(commit=False)
        vehicule.updated_by = user
        vehicule.save()
        messages.success(request, "Le véhicule a été modifié.")
        return redirect("vehicule:index")
    context = _layout_context(user)
    context.update({"form": form, "page_title": "Modifier le véhicule", "vehicule": vehicule})
    return render(request, "vehicule/form.html", context)


def vehicule_delete(request, pk):
    user = _connected_user(request)
    if user is None:
        return redirect("authentication:connexion")
    vehicule = get_object_or_404(
        Vehicule,
        pk=pk,
        entreprise=user.entreprise,
        deleted_at__isnull=True,
    )
    if request.method == "POST":
        vehicule.deleted_at = timezone.now()
        vehicule.deleted_by = user
        vehicule.save(update_fields=["deleted_at", "deleted_by", "updated_at"])
        messages.success(request, "Le véhicule a été supprimé.")
    return redirect("vehicule:index")
