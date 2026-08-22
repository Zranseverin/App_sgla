from django.urls import path
from . import views


app_name = "entreprises"

urlpatterns = [path("track/", views.track_visitor_event, name="track_visitor_event")]
