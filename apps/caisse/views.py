from django.contrib import messages
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.authentication.models import User
from apps.passage.models import Passage
from .forms import EncaissementPassageForm, MouvementCaisseForm
from .models import MouvementCaisse


def _connected_user(request):
    return User.objects.select_related("entreprise__plan", "role").filter(pk=request.session.get("utilisateur_id"), statut="actif").first()


def _layout(user):
    entreprise = user.entreprise
    jours = max((entreprise.date_fin_essai - timezone.localdate()).days, 0) if entreprise.date_fin_essai else 0
    return {"user": user, "entreprise": entreprise, "plan": entreprise.plan, "stats": {"jours_restants": jours}, "user_initials": "".join(x[0].upper() for x in user.nom.split()[:2])}


def caisse_list(request):
    user = _connected_user(request)
    if not user:
        return redirect("authentication:connexion")
    mouvements = MouvementCaisse.objects.filter(entreprise=user.entreprise).select_related("created_by")
    query = request.GET.get("q", "").strip()
    type_mouvement = request.GET.get("type", "")
    if query:
        mouvements = mouvements.filter(Q(motif__icontains=query) | Q(reference__icontains=query))
    if type_mouvement in {"entree", "sortie"}:
        mouvements = mouvements.filter(type_mouvement=type_mouvement)
    totals = mouvements.values("type_mouvement").annotate(total=Sum("montant"))
    amounts = {row["type_mouvement"]: row["total"] for row in totals}
    entrees, sorties = amounts.get("entree", 0), amounts.get("sortie", 0)
    context = _layout(user)
    context.update({"mouvements": mouvements, "entrees": entrees, "sorties": sorties, "solde": entrees - sorties, "query": query, "selected_type": type_mouvement})
    return render(request, "caisse/index.html", context)


def mouvement_create(request):
    user = _connected_user(request)
    if not user:
        return redirect("authentication:connexion")
    form = MouvementCaisseForm(request.POST or None, initial={"date_mouvement": timezone.localtime().strftime("%Y-%m-%dT%H:%M")})
    if request.method == "POST" and form.is_valid():
        mouvement = form.save(commit=False)
        mouvement.entreprise = user.entreprise
        mouvement.type_mouvement = "sortie"
        mouvement.created_by = user
        mouvement.save()
        messages.success(request, "Le mouvement de caisse a été enregistré.")
        return redirect("caisse:index")
    context = _layout(user)
    context.update({"form": form})
    return render(request, "caisse/form.html", context)


def encaisser_passage(request, passage_id):
    user = _connected_user(request)
    if not user:
        return redirect("authentication:connexion")
    passage = get_object_or_404(
        Passage,
        pk=passage_id,
        entreprise=user.entreprise,
        deleted_at__isnull=True,
    )
    if passage.statut == "annule" or passage.statut_reglement == "paye":
        messages.info(request, "Ce passage ne nécessite plus d’encaissement.")
        return redirect("caisse:index")
    form = EncaissementPassageForm(
        request.POST or None,
        montant_restant=passage.montant_restant,
        initial={"mode_reglement": passage.mode_reglement},
    )
    if request.method == "POST" and form.is_valid():
        passage.montant_paye += form.cleaned_data["montant"]
        passage.mode_reglement = form.cleaned_data["mode_reglement"]
        passage.statut_reglement = "paye" if passage.montant_paye >= passage.montant_total else "partiel"
        passage.updated_by = user
        passage.save()
        messages.success(request, f"Le versement du passage #{passage.pk} a été encaissé.")
        return redirect("caisse:index")
    context = _layout(user)
    context.update({"form": form, "passage": passage})
    return render(request, "caisse/encaisser.html", context)
