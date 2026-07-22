from django.urls import path
from . import views

app_name = "caisse"
urlpatterns = [
    path("", views.caisse_list, name="index"),
    path("mouvement/creer/", views.mouvement_create, name="create"),
    path("passage/<int:passage_id>/encaisser/", views.encaisser_passage, name="encaisser_passage"),
]
