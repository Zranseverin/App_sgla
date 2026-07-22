from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.authentication.models import User
from apps.roles.models import Role


def index(request):
    """Tableau de bord principal de l'entreprise connectée."""
    utilisateur_id = request.session.get("utilisateur_id")
    user = User.objects.select_related("entreprise__plan", "role").filter(
        pk=utilisateur_id,
        statut="actif",
    ).first()
    if user is None:
        messages.info(request, "Connectez-vous pour accéder au tableau de bord.")
        return redirect("authentication:connexion")

    entreprise = user.entreprise
    today = timezone.localdate()
    jours_restants = (
        max((entreprise.date_fin_essai - today).days, 0)
        if entreprise.date_fin_essai
        else 0
    )

    stats = {
        "total_users": User.objects.filter(entreprise=entreprise).count(),
        "active_users": User.objects.filter(
            entreprise=entreprise,
            statut="actif",
        ).count(),
        "total_roles": Role.objects.filter(entreprise=entreprise).count(),
        "jours_restants": jours_restants,
    }
    stats["inactive_users"] = stats["total_users"] - stats["active_users"]

    recent_users = User.objects.filter(entreprise=entreprise).select_related(
        "role",
    ).order_by("-created_at")[:5]
    role_breakdown = [
        {"label": role.libelle, "count": role.utilisateurs.count()}
        for role in Role.objects.filter(entreprise=entreprise).prefetch_related(
            "utilisateurs",
        ).order_by("libelle")
    ]

    return render(request, "dashboard/index.html", {
        "user": user,
        "entreprise": entreprise,
        "plan": entreprise.plan,
        "stats": stats,
        "recent_users": recent_users,
        "role_breakdown": role_breakdown,
        "today": today,
        "user_initials": "".join(
            part[0].upper() for part in user.nom.split()[:2] if part
        ),
    })
