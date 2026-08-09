"""homestead serializers."""
from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from apps.homestead.models import (
    Appliance,
    HouseholdCost,
    Improvement,
    InsurancePolicy,
    MaintenanceTask,
    Property,
    RoomArea,
    RoomPlanItem,
    RoomPlanProduct,
    ServiceProvider,
)


def _non_blank(value: str) -> str:
    if not value.strip():
        raise serializers.ValidationError("This field may not be blank.")
    return value


def _web_url(value: str) -> str:
    """Accept only http(s) links.

    These values are rendered as `href`/`src` in the browser, so a `javascript:` or `data:`
    URL saved here would execute in another household member's session when they click the
    product. Blank stays blank — the field is optional.
    """
    value = value.strip()
    if not value:
        return ""
    if not value.lower().startswith(("http://", "https://")):
        raise serializers.ValidationError("Enter a link starting with http:// or https://.")
    return value


class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = [
            "id", "name", "address", "property_type", "tenure", "purchase_date",
            "move_in_date", "year_built", "is_primary", "notes", "water_shutoff",
            "gas_shutoff", "electricity_consumer_unit", "boiler_location", "visibility",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        return _non_blank(value)


class ServiceProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceProvider
        fields = [
            "id", "name", "trade", "company", "phone", "email", "website",
            "last_used_at", "notes", "visibility", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        return _non_blank(value)


class ApplianceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appliance
        fields = [
            "id", "name", "category", "brand", "model_number",
            "serial_number", "room", "purchase_date", "warranty_expires_at",
            "warranty_provider", "manual_url", "notes", "visibility",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        return _non_blank(value)


class MaintenanceTaskSerializer(serializers.ModelSerializer):
    # DRF treats a bare `<fk>_id` in `fields` as read-only; declare it so writes land.
    appliance_id = serializers.IntegerField(required=False, allow_null=True)
    provider_id = serializers.IntegerField(required=False, allow_null=True)
    assigned_to_person_id = serializers.IntegerField(required=False, allow_null=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = MaintenanceTask
        fields = [
            "id", "appliance_id", "provider_id", "assigned_to_person_id",
            "title", "category", "next_due_at", "is_all_day", "recurrence_rule",
            "last_done_at", "notes", "solace_bill_ref", "is_overdue", "calendar_event_id", "visibility",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "solace_bill_ref", "is_overdue", "calendar_event_id", "created_at", "updated_at",
        ]

    def validate_title(self, value: str) -> str:
        return _non_blank(value)


class MaintenanceCostRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    category = serializers.CharField(max_length=80, default="other")

    def validate_category(self, value: str) -> str:
        return _non_blank(value)


class ImprovementSerializer(serializers.ModelSerializer):
    assigned_to_person_id = serializers.IntegerField(required=False, allow_null=True)
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = Improvement
        fields = [
            "id", "assigned_to_person_id", "title", "description", "status",
            "priority", "room", "target_date", "is_all_day", "project_ref", "notes",
            "is_open", "calendar_event_id", "visibility", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "is_open", "calendar_event_id", "created_at", "updated_at",
        ]

    def validate_title(self, value: str) -> str:
        return _non_blank(value)


class RoomCostSummarySerializer(serializers.Serializer):
    active_count = serializers.IntegerField()
    completed_count = serializers.IntegerField()
    archived_count = serializers.IntegerField()
    remaining_estimated_cost = serializers.DecimalField(max_digits=14, decimal_places=2)
    completed_cost = serializers.DecimalField(max_digits=14, decimal_places=2)
    overall_cost = serializers.DecimalField(max_digits=14, decimal_places=2)


class RoomAreaSerializer(serializers.ModelSerializer):
    summary = serializers.SerializerMethodField()

    class Meta:
        model = RoomArea
        fields = [
            "id", "name", "area_type", "description", "icon", "colour",
            "display_order", "floorplan_data", "visibility", "summary",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "summary", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        return _non_blank(value)

    def get_summary(self, obj: RoomArea) -> dict:
        summaries = self.context.get("summaries", {})
        return summaries.get(obj.id, self.context.get("empty_summary", {
            "active_count": 0,
            "completed_count": 0,
            "archived_count": 0,
            "remaining_estimated_cost": "0.00",
            "completed_cost": "0.00",
            "overall_cost": "0.00",
        }))


class RoomPlanProductSerializer(serializers.ModelSerializer):
    plan_item_id = serializers.IntegerField(read_only=True)
    total_cost = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = RoomPlanProduct
        fields = [
            "id", "plan_item_id", "title", "url", "image_url", "retailer",
            "quantity", "unit_cost", "total_cost", "is_chosen", "notes", "position",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "plan_item_id", "total_cost", "created_at", "updated_at"]

    def validate_title(self, value: str) -> str:
        return _non_blank(value)

    def validate_url(self, value: str) -> str:
        return _web_url(value)

    def validate_image_url(self, value: str) -> str:
        return _web_url(value)


class RoomPlanItemSerializer(serializers.ModelSerializer):
    room_id = serializers.IntegerField(read_only=True)
    assigned_to_person_id = serializers.IntegerField(required=False, allow_null=True)
    estimated_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    effective_cost = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    products = RoomPlanProductSerializer(many=True, read_only=True)

    class Meta:
        model = RoomPlanItem
        fields = [
            "id", "room_id", "assigned_to_person_id", "title", "item_type", "status",
            "priority", "description", "quantity", "estimated_unit_cost", "estimated_total",
            "actual_cost", "effective_cost", "notes", "position",
            "completed_at", "visibility", "products", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "room_id", "estimated_total", "effective_cost", "completed_at",
            "products", "created_at", "updated_at",
        ]

    def validate_title(self, value: str) -> str:
        return _non_blank(value)


class InsurancePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = InsurancePolicy
        fields = [
            "id", "name", "policy_type", "provider", "policy_number",
            "premium_amount", "billing_cycle", "next_renewal_at", "recurrence_rule",
            "standard_excess", "additional_excesses", "coverage_summary",
            "contact_phone", "portal_url", "is_active", "solace_bill_ref",
            "notes", "visibility", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "solace_bill_ref", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        return _non_blank(value)


class HouseholdCostSerializer(serializers.ModelSerializer):
    class Meta:
        model = HouseholdCost
        fields = [
            "id", "name", "cost_type", "provider", "account_number", "amount",
            "billing_cycle", "next_due_at", "recurrence_rule", "is_active",
            "solace_bill_ref", "notes", "visibility", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "solace_bill_ref", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        return _non_blank(value)
