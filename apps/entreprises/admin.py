from django.contrib import admin
from .models import VisitorEvent

@admin.register(VisitorEvent)
class VisitorEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "event_type", "visitor_id", "ip_address", "device_label", "entreprise", "locality")
    list_filter = ("event_type", "created_at", "entreprise")
    search_fields = ("visitor_id", "ip_address", "search_query", "locality", "user_agent")
    readonly_fields = tuple(field.name for field in VisitorEvent._meta.fields)
