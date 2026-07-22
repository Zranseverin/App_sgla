from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.authentication.models import User

from .forms import TypeLavageForm
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
    form = TypeLavageForm(
        request.POST or None,
        entreprise=user.entreprise,
    )
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.entreprise = user.entreprise
        item.user = user
        item.created_by = user
        item.updated_by = user
        item.save()
        messages.success(request, "Le type de lavage a été créé.")
        return redirect("type_lavage:index")
    context = _layout_context(user)
    context.update({"form": form, "page_title": "Créer un type de lavage"})
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
