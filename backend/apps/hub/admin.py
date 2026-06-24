from django.contrib import admin

from apps.hub.models import HouseholdHubWidget, HubWidget, UserHubWidget


@admin.register(HubWidget)
class HubWidgetAdmin(admin.ModelAdmin):
    list_display = ["key", "name", "supports_kiosk", "display_order"]


@admin.register(HouseholdHubWidget)
class HouseholdHubWidgetAdmin(admin.ModelAdmin):
    list_display = ["household", "widget", "is_enabled", "display_order", "size"]


@admin.register(UserHubWidget)
class UserHubWidgetAdmin(admin.ModelAdmin):
    list_display = ["user", "widget", "is_enabled", "display_order"]
