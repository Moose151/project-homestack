from django.contrib import admin

from apps.homestead.models import (
    Appliance,
    HouseholdCost,
    Improvement,
    InsurancePolicy,
    MaintenanceTask,
    Property,
    RoomArea,
    RoomPlanItem,
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


@admin.register(RoomArea)
class RoomAreaAdmin(admin.ModelAdmin):
    list_display = ("name", "area_type", "display_order", "visibility")
    search_fields = ("name", "description")
    list_filter = ("area_type", "visibility")


@admin.register(RoomPlanItem)
class RoomPlanItemAdmin(admin.ModelAdmin):
    list_display = (
        "title", "room", "item_type", "status", "priority",
        "estimated_unit_cost", "actual_cost",
    )
    search_fields = ("title", "description", "notes")
    list_filter = ("item_type", "status", "priority", "visibility")


@admin.register(InsurancePolicy)
class InsurancePolicyAdmin(admin.ModelAdmin):
    list_display = (
        "name", "policy_type", "provider", "premium_amount",
        "next_renewal_at", "is_active", "solace_bill_ref",
    )
    search_fields = ("name", "provider", "policy_number", "notes")
    list_filter = ("policy_type", "billing_cycle", "is_active")


@admin.register(HouseholdCost)
class HouseholdCostAdmin(admin.ModelAdmin):
    list_display = (
        "name", "cost_type", "provider", "amount",
        "next_due_at", "is_active", "solace_bill_ref",
    )
    search_fields = ("name", "provider", "account_number", "notes")
    list_filter = ("cost_type", "billing_cycle", "is_active")
