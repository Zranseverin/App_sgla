from django.urls import path

from . import views


app_name = "platform_admin"

urlpatterns = [
    path("connexion/", views.admin_login, name="login"),
    path("deconnexion/", views.admin_logout, name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("visiteurs/", views.visitor_analytics, name="visitor_analytics"),
    path("plans/", views.plan_list, name="plan_list"),
    path("plans/creer/", views.plan_create, name="plan_create"),
    path("plans/<int:pk>/modifier/", views.plan_edit, name="plan_edit"),
    path("plans/<int:pk>/statut/", views.plan_toggle, name="plan_toggle"),
    path("configuration-mail/", views.mail_configuration, name="mail_configuration"),
    path("configuration-mail/tester/", views.test_mail_configuration, name="test_mail_configuration"),
    path("entreprises/creer/", views.create_enterprise, name="create_enterprise"),
    path("entreprises/<int:pk>/", views.enterprise_detail, name="enterprise_detail"),
    path("entreprises/<int:pk>/activer/", views.activate_subscription, name="activate_subscription"),
    path("entreprises/<int:pk>/suspendre/", views.suspend_subscription, name="suspend_subscription"),
]
