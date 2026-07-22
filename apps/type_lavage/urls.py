from django.urls import path

from . import views

app_name = "type_lavage"

urlpatterns = [
    path("", views.type_lavage_list, name="index"),
    path("creer/", views.type_lavage_create, name="create"),
    path("<int:pk>/modifier/", views.type_lavage_update, name="update"),
    path("<int:pk>/supprimer/", views.type_lavage_delete, name="delete"),
]
