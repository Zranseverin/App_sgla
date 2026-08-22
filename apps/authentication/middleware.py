from django.shortcuts import redirect
from django.urls import Resolver404, resolve

from .models import User


class SubscriptionAccessMiddleware:
    """Bloque les pages métier lorsque l'accès de l'entreprise est expiré."""

    EXEMPT_URL_NAMES = {
        "accueil",
        "connexion",
        "inscription",
        "google_auth_start",
        "google_auth_callback",
        "forgot_password",
        "reset_password",
        "deconnexion",
        "subscription_expired",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            match = resolve(request.path_info)
        except Resolver404:
            match = None
        if self._is_exempt(request, match):
            return self.get_response(request)

        user_id = request.session.get("utilisateur_id")
        if user_id:
            user = User.objects.select_related("entreprise").filter(
                pk=user_id, statut="actif"
            ).first()
            if user and not user.entreprise.abonnement_est_actif():
                return redirect("authentication:subscription_expired")

        return self.get_response(request)

    def _is_exempt(self, request, match):
        if request.path.startswith(("/static/", "/media/", "/admin/", "/cleango-admin/")):
            return True
        if match and match.url_name == "configuration":
            return request.GET.get("tab") == "subscription"
        return bool(match and match.url_name in self.EXEMPT_URL_NAMES)
