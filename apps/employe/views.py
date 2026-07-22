from calendar import monthrange
from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.authentication.models import User
from apps.passage.models import Passage
from .forms import EmployeForm
from .models import Employe


def _connected_user(request):
    return User.objects.select_related("entreprise__plan", "role").filter(pk=request.session.get("utilisateur_id"), statut="actif").first()


def _context(user):
    entreprise = user.entreprise
    jours = max((entreprise.date_fin_essai - timezone.localdate()).days, 0) if entreprise.date_fin_essai else 0
    return {"user": user, "entreprise": entreprise, "plan": entreprise.plan, "stats": {"jours_restants": jours}, "user_initials": "".join(x[0].upper() for x in user.nom.split()[:2])}


def employe_list(request):
    user = _connected_user(request)
    if not user:
        return redirect("authentication:connexion")
    employes = Employe.objects.filter(entreprise=user.entreprise).select_related("user", "user__role")
    query = request.GET.get("q", "").strip()
    statut = request.GET.get("statut", "")
    if query:
        employes = employes.filter(Q(user__nom__icontains=query) | Q(user__matricule__icontains=query) | Q(poste__icontains=query))
    if statut:
        employes = employes.filter(statut=statut)
    selected = employes.filter(pk=request.GET.get("employe")).first() if request.GET.get("employe") else employes.first()
    active_tab = request.GET.get("tab", "fiches")
    if active_tab not in {"fiches", "bulletins"}:
        active_tab = "fiches"

    today = timezone.localdate()
    month_names = ("", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre")
    start_date = today.replace(day=1)
    end_date = today.replace(day=monthrange(today.year, today.month)[1])
    commissions = Passage.objects.none()
    if selected:
        commissions = Passage.objects.filter(
            entreprise=user.entreprise,
            employe_realisateur=selected.user,
            date_heure_debut__date__range=(start_date, end_date),
            deleted_at__isnull=True,
        ).exclude(statut="annule").select_related("client", "vehicule", "type_lavage")

    total_commissions = commissions.aggregate(total=Sum("commission_employe"))["total"] or Decimal("0")
    salaire_brut = selected.salaire_brut if selected else Decimal("0")
    cotisation_cnps = (salaire_brut * Decimal("0.063")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    bulletin = {
        "mois": f"{month_names[today.month]} {today.year}",
        "statut": "Calcul automatique",
        "salaire_brut": salaire_brut,
        "primes_missions": total_commissions,
        "nombre_missions": commissions.count(),
        "cotisation_cnps": cotisation_cnps,
        "net_a_payer": salaire_brut + total_commissions - cotisation_cnps,
    }
    primes = []
    for passage in commissions:
        validated = passage.statut == "termine" and passage.statut_reglement == "paye"
        primes.append({
            "icone": "✓" if validated else "🏆",
            "titre": f"Commission passage #{passage.pk} · {passage.client.nom_complet}",
            "detail": f"{passage.vehicule.immatriculation} · {passage.type_lavage.libelle} · {passage.get_statut_display()}",
            "montant": passage.commission_employe,
            "statut": "Validée" if validated else "En attente",
            "status_class": "validated" if validated else "pending",
        })
    context = _context(user)
    context.update({
        "employes": employes,
        "selected": selected,
        "query": query,
        "selected_statut": statut,
        "statuts_employe": Employe.STATUTS,
        "total": employes.count(),
        "active_tab": active_tab,
        "bulletin": bulletin,
        "primes": primes,
    })
    return render(request, "employe/index.html", context)


def _save(request, instance=None):
    user = _connected_user(request)
    if not user:
        return redirect("authentication:connexion")
    form = EmployeForm(request.POST or None, instance=instance, entreprise=user.entreprise)
    if request.method == "POST" and form.is_valid():
        employe = form.save(commit=False)
        employe.entreprise = user.entreprise
        employe.updated_by = user
        if not employe.pk:
            employe.created_by = user
        employe.save()
        messages.success(request, "La fiche employé a été enregistrée.")
        return redirect(f"/employes/?employe={employe.pk}")
    context = _context(user)
    context.update({
        "form": form,
        "page_title": "Modifier l’employé" if instance else "Créer une fiche employé",
        "user_postes": {
            str(account.pk): account.role.libelle
            for account in form.fields["user"].queryset.select_related("role")
        },
    })
    return render(request, "employe/form.html", context)


def employe_create(request):
    return _save(request)


def employe_update(request, pk):
    user = _connected_user(request)
    if not user:
        return redirect("authentication:connexion")
    instance = get_object_or_404(Employe, pk=pk, entreprise=user.entreprise)
    return _save(request, instance)
