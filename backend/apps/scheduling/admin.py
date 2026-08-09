from django.contrib import admin

from apps.scheduling.models import CalendarEvent, RotatingSchedule, RotatingScheduleException


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ["title", "start_at", "end_at", "visibility", "is_synced", "source_record_type"]
    list_filter = ["visibility", "sensitivity", "is_all_day"]
    search_fields = ["title", "description"]
    readonly_fields = ["source_node", "source_record_type", "source_record_id", "created_at", "updated_at"]


@admin.register(RotatingSchedule)
class RotatingScheduleAdmin(admin.ModelAdmin):
    list_display = ["title", "anchor_date", "cycle_pattern", "is_active", "visibility"]
    list_filter = ["is_active", "visibility"]
    search_fields = ["title", "primary_label", "secondary_label"]
    filter_horizontal = ["people"]


@admin.register(RotatingScheduleException)
class RotatingScheduleExceptionAdmin(admin.ModelAdmin):
    list_display = ["schedule", "date", "state", "note"]
    list_filter = ["state", "schedule"]
