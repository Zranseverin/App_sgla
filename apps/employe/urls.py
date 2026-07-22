from django.urls import path
from . import views

app_name = "employe"
urlpatterns = [
    path("", views.employe_list, name="index"),
    path("creer/", views.employe_create, name="create"),
    path("<int:pk>/modifier/", views.employe_update, name="update"),
]
