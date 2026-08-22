from django.urls import path

from . import views


app_name = "authentication"

urlpatterns = [
    path("", views.login_view, name="accueil"),
    path("connexion/", views.login_view, name="connexion"),
    path("inscription/", views.company_register_view, name="inscription"),
    path("auth/google/", views.google_auth_start, name="google_auth_start"),
    path("auth/google/callback/", views.google_auth_callback, name="google_auth_callback"),
    path("mot-de-passe-oublie/", views.forgot_password_view, name="forgot_password"),
    path("reinitialiser/<str:token>/", views.reset_password_view, name="reset_password"),
    path("profil/", views.connected_profile_view, name="profile"),
    path("profil/modifier/", views.edit_connected_profile_view, name="edit_profile"),
    path("parametres/entreprise/", views.enterprise_settings_view, name="enterprise_settings"),
    path("parametres/entreprise/modifier/", views.edit_enterprise_settings_view, name="edit_enterprise_settings"),
    path("configuration/", views.configuration_hub_view, name="configuration"),
    path("abonnement-expire/", views.subscription_expired_view, name="subscription_expired"),
    path("deconnexion/", views.logout_view, name="deconnexion"),
]
