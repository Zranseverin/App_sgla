from django.urls import path

from . import views

app_name = "vehicule"

urlpatterns = [
    path("", views.vehicule_list, name="index"),
    path("creer/", views.vehicule_create, name="create"),
    path("<int:pk>/modifier/", views.vehicule_update, name="update"),
    path("<int:pk>/supprimer/", views.vehicule_delete, name="delete"),
]
