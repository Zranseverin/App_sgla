import secrets

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.authentication.models import User

from .forms import ClientForm
from .models import Client


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


def client_list(request):
    user = _connected_user(request)
    if user is None:
        return redirect("authentication:connexion")
    clients = Client.objects.filter(
        entreprise=user.entreprise,
        deleted_at__isnull=True,
    )
    query = request.GET.get("q", "").strip()
    if query:
        clients = clients.filter(
            Q(code__icontains=query)
            | Q(nom_complet__icontains=query)
            | Q(telephone__icontains=query)
            | Q(email__icontains=query)
        )
    context = _layout_context(user)
    context.update({
        "clients": clients,
        "total": clients.count(),
        "query": query,
    })
    return render(request, "client/index.html", context)


def client_create(request):
    user = _connected_user(request)
    if user is None:
        return redirect("authentication:connexion")
    form = ClientForm(request.POST or None, entreprise=user.entreprise)
    if request.method == "POST" and form.is_valid():
        client = form.save(commit=False)
        client.code = f"CLI-{secrets.token_hex(3).upper()}"
        client.entreprise = user.entreprise
        client.user = user
        client.created_by = user
        client.updated_by = user
        client.save()
        messages.success(request, f"Le client {client.nom_complet} a été créé.")
        return redirect("client:index")
    context = _layout_context(user)
    context.update({"form": form, "page_title": "Créer un client"})
    return render(request, "client/form.html", context)


def client_update(request, pk):
    user = _connected_user(request)
    if user is None:
        return redirect("authentication:connexion")
    client = get_object_or_404(
        Client,
        pk=pk,
        entreprise=user.entreprise,
        deleted_at__isnull=True,
    )
    form = ClientForm(request.POST or None, instance=client, entreprise=user.entreprise)
    if request.method == "POST" and form.is_valid():
        client = form.save(commit=False)
        client.updated_by = user
        client.save()
        messages.success(request, "Le client a été modifié.")
        return redirect("client:index")
    context = _layout_context(user)
    context.update({"form": form, "page_title": "Modifier le client", "client": client})
    return render(request, "client/form.html", context)


def client_delete(request, pk):
    user = _connected_user(request)
    if user is None:
        return redirect("authentication:connexion")
    client = get_object_or_404(
        Client,
        pk=pk,
        entreprise=user.entreprise,
        deleted_at__isnull=True,
    )
    if request.method == "POST":
        client.deleted_at = timezone.now()
        client.deleted_by = user
        client.save(update_fields=["deleted_at", "deleted_by", "updated_at"])
        messages.success(request, "Le client a été supprimé.")
    return redirect("client:index")
