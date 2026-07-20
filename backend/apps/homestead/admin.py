from django.contrib import admin

from apps.homestead.models import (
    Appliance,
    Improvement,
    MaintenanceTask,
    Property,
    ServiceProvider,
)


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("name", "property_type", "tenure", "is_primary")
    search_fields = ("name", "address")
    list_filter = ("property_type", "tenure")


@admin.register(ServiceProvider)
class ServiceProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "trade", "company", "phone")
    search_fields = ("name", "company", "notes")
    list_filter = ("trade",)


@admin.register(Appliance)
class ApplianceAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "brand", "warranty_expires_at")
    search_fields = ("name", "brand", "model_number", "serial_number")
    list_filter = ("category",)


@admin.register(MaintenanceTask)
class MaintenanceTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "next_due_at", "last_done_at")
    search_fields = ("title", "notes")
    list_filter = ("category",)


@admin.register(Improvement)
class ImprovementAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "priority", "room", "target_date")
    search_fields = ("title", "description", "notes")
    list_filter = ("status", "priority")
