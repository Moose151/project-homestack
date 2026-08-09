from django.contrib import admin

from apps.atlas.models import AtlasList, AtlasListItem, AtlasNote, AtlasReminder


@admin.register(AtlasNote)
class AtlasNoteAdmin(admin.ModelAdmin):
    list_display = ["title", "visibility", "sensitivity", "updated_at"]
    list_filter = ["visibility", "sensitivity"]
    search_fields = ["title", "body"]


@admin.register(AtlasList)
class AtlasListAdmin(admin.ModelAdmin):
    list_display = ["title", "list_type", "visibility", "updated_at"]
    list_filter = ["list_type", "visibility"]


@admin.register(AtlasListItem)
class AtlasListItemAdmin(admin.ModelAdmin):
    # A M2M cannot appear in list_display; assignees are edited on the detail page.
    list_display = ["title", "atlas_list", "is_complete", "position"]
    filter_horizontal = ["assigned_to_people"]
    list_filter = ["atlas_list"]
    search_fields = ["title"]


@admin.register(AtlasReminder)
class AtlasReminderAdmin(admin.ModelAdmin):
    list_display = ["title", "due_at", "visibility", "calendar_event_id"]
    list_filter = ["visibility", "sensitivity"]
    search_fields = ["title", "body"]
    readonly_fields = ["calendar_event_id"]
