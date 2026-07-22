from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

urlpatterns = [
    path("", include("apps.authentication.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("types-lavage/", include("apps.type_lavage.urls")),
    path("clients/", include("apps.client.urls")),
    path("vehicules/", include("apps.vehicule.urls")),
    path("passages/", include("apps.passage.urls")),
    path("employes/", include("apps.employe.urls")),
    path("caisse/", include("apps.caisse.urls")),
    path("factures/", include("apps.facture.urls")),
    path("admin/", admin.site.urls),
    path("api/core/", include("apps.core.urls")),
    path("api/entreprises/", include("apps.entreprises.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
