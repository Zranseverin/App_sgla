from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.authentication.models import User

from .forms import TypeLavageBatchHeaderForm, TypeLavageForm, TypeLavageLineFormSet
from .models import TypeLavage


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


def type_lavage_list(request):
    user = _connected_user(request)
    if user is None:
        return redirect("authentication:connexion")
    types = TypeLavage.objects.filter(
        entreprise=user.entreprise,
        deleted_at__isnull=True,
    ).select_related("created_by", "updated_by")
    context = _layout_context(user)
    context.update({
        "types_lavage": types,
        "total": types.count(),
        "actifs": types.filter(actif=True).count(),
        "inactifs": types.filter(actif=False).count(),
    })
    return render(request, "type_lavage/index.html", context)


def type_lavage_create(request):
    user = _connected_user(request)
    if user is None:
        return redirect("authentication:connexion")
    header_form = TypeLavageBatchHeaderForm(request.POST or None)
    selected_vehicle = request.POST.get("type_vehicule", "tous")
    formset = TypeLavageLineFormSet(request.POST or None, prefix="services", entreprise=user.entreprise, type_vehicule=selected_vehicle)
    if request.method == "POST" and header_form.is_valid() and formset.is_valid():
        vehicle = header_form.cleaned_data["type_vehicule"]
        items = []
        with transaction.atomic():
            for line in formset.cleaned_data:
                if not line or line.get("DELETE"):
                    continue
                items.append(TypeLavage.objects.create(
                    entreprise=user.entreprise, user=user, created_by=user, updated_by=user,
                    type_vehicule=vehicle, libelle=line["libelle"], description=line.get("description") or "",
                    prix_unitaire=line["prix_unitaire"], duree_estimee_min=line["duree_estimee_min"], actif=line.get("actif", False),
                ))
        messages.success(request, f"{len(items)} prestation{'s' if len(items) > 1 else ''} créée{'s' if len(items) > 1 else ''}.")
        return redirect("type_lavage:index")
    context = _layout_context(user)
    context.update({"header_form": header_form, "formset": formset, "page_title": "Créer des types de lavage", "bulk_create": True})
    return render(request, "type_lavage/form.html", context)


def type_lavage_update(request, pk):
    user = _connected_user(request)
    if user is None:
        return redirect("authentication:connexion")
    item = get_object_or_404(
        TypeLavage,
        pk=pk,
        entreprise=user.entreprise,
        deleted_at__isnull=True,
    )
    form = TypeLavageForm(
        request.POST or None,
        instance=item,
        entreprise=user.entreprise,
    )
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.updated_by = user
        item.save()
        messages.success(request, "Le type de lavage a été modifié.")
        return redirect("type_lavage:index")
    context = _layout_context(user)
    context.update({"form": form, "page_title": "Modifier le type de lavage", "item": item})
    return render(request, "type_lavage/form.html", context)


def type_lavage_delete(request, pk):
    user = _connected_user(request)
    if user is None:
        return redirect("authentication:connexion")
    item = get_object_or_404(
        TypeLavage,
        pk=pk,
        entreprise=user.entreprise,
        deleted_at__isnull=True,
    )
    if request.method == "POST":
        item.deleted_at = timezone.now()
        item.deleted_by = user
        item.actif = False
        item.save(update_fields=["deleted_at", "deleted_by", "actif", "updated_at"])
        messages.success(request, "Le type de lavage a été supprimé.")
    return redirect("type_lavage:index")
