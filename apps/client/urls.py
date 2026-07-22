from django.urls import path

from . import views

app_name = "client"

urlpatterns = [
    path("", views.client_list, name="index"),
    path("creer/", views.client_create, name="create"),
    path("<int:pk>/modifier/", views.client_update, name="update"),
    path("<int:pk>/supprimer/", views.client_delete, name="delete"),
]
