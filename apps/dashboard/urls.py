from django.urls import path

from . import views


app_name = "dashboard"

urlpatterns = [
    path("", views.index, name="home"),
    path("index/", views.index, name="index"),
    path("reporting/", views.reporting, name="reporting"),
]
