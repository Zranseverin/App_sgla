from apps.authentication.models import User
from apps.passage.models import Passage


def passage_notifications(request):
    """Expose les passages actifs de l'entreprise dans tous les headers."""
    user_id = request.session.get("utilisateur_id")
    entreprise_id = User.objects.filter(
        pk=user_id,
        statut="actif",
    ).values_list("entreprise_id", flat=True).first()
    if not entreprise_id:
        return {"notification_passages": (), "notification_passages_count": 0}

    passages = Passage.objects.filter(
        entreprise_id=entreprise_id,
        statut__in=("en_attente", "en_cours"),
        deleted_at__isnull=True,
    ).select_related("client", "vehicule", "type_lavage")
    return {
        "notification_passages": passages[:8],
        "notification_passages_count": passages.count(),
    }
