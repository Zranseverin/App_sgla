from django.urls import path
from . import views

app_name = "facture"
urlpatterns = [
    path("", views.facture_list, name="index"),
    path("creer/", views.facture_create, name="create"),
    path("<int:pk>/", views.facture_detail, name="detail"),
    path("<int:pk>/pdf/", views.facture_pdf, name="pdf"),
]
