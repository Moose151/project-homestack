from django.contrib import admin

from apps.scheduling.models import CalendarEvent


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ["title", "start_at", "end_at", "visibility", "is_synced", "source_record_type"]
    list_filter = ["visibility", "sensitivity", "is_all_day"]
    search_fields = ["title", "description"]
    readonly_fields = ["source_node", "source_record_type", "source_record_id", "created_at", "updated_at"]
