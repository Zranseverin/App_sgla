from django.urls import path

from . import views

app_name = "passage"

urlpatterns = [
    path("", views.passage_list, name="index"),
    path("creer/", views.passage_create, name="create"),
    path("<int:pk>/modifier/", views.passage_update, name="update"),
    path("<int:pk>/statut/", views.passage_change_status, name="change_status"),
    path("<int:pk>/supprimer/", views.passage_delete, name="delete"),
    path("vehicules-par-client/<int:client_id>/", views.vehicles_by_client, name="vehicles_by_client"),
]
