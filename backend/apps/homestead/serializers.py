"""homestead serializers."""
from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from apps.core.serializers import AssigneeSerializerMixin

from apps.homestead.models import (
    Appliance,
    HouseholdCost,
    Improvement,
    InsurancePolicy,
    MaintenanceTask,
    Pool,
    Property,
    RoomArea,
    RoomPlanItem,
    RoomPlanProduct,
    ServiceProvider,
    UtilityBill,
    WaterTest,
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


class MaintenanceTaskSerializer(AssigneeSerializerMixin, serializers.ModelSerializer):
    # DRF treats a bare `<fk>_id` in `fields` as read-only; declare it so writes land.
    appliance_id = serializers.IntegerField(required=False, allow_null=True)
    provider_id = serializers.IntegerField(required=False, allow_null=True)
    pool_id = serializers.IntegerField(required=False, allow_null=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = MaintenanceTask
        fields = [
            "id", "appliance_id", "provider_id", "pool_id", "assigned_to_person_ids",
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


class ImprovementSerializer(AssigneeSerializerMixin, serializers.ModelSerializer):
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = Improvement
        fields = [
            "id", "assigned_to_person_ids", "title", "description", "status",
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
    cached_image_url = serializers.SerializerMethodField()
    price_watch = serializers.SerializerMethodField()
    cache_image = serializers.BooleanField(write_only=True, required=False, default=False)
    price_watch_enabled = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = RoomPlanProduct
        fields = [
            "id", "plan_item_id", "title", "url", "image_url", "source_image_url",
            "cached_image_url", "image_attachment_id", "retailer", "currency", "imported_at", "price_watch",
            "cache_image", "price_watch_enabled",
            "quantity", "unit_cost", "total_cost", "is_chosen", "is_purchased",
            "actual_cost", "notes", "position", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "plan_item_id", "cached_image_url", "image_attachment_id", "imported_at", "price_watch", "total_cost", "created_at", "updated_at"]

    def validate_title(self, value: str) -> str:
        return _non_blank(value)

    def validate_url(self, value: str) -> str:
        return _web_url(value)

    def validate_image_url(self, value: str) -> str:
        return _web_url(value)

    def get_cached_image_url(self, obj):
        return f"/api/v1/attachments/{obj.image_attachment_id}/download/" if obj.image_attachment_id else ""

    def get_price_watch(self, obj):
        from apps.link_imports.models import LinkWatch
        from apps.link_imports.services import serialize_watch
        return serialize_watch(LinkWatch.objects.filter(
            source_node="homestead", source_record_type="RoomPlanProduct", source_record_id=obj.id,
        ).first())


class RoomPlanItemSerializer(AssigneeSerializerMixin, serializers.ModelSerializer):
    room_id = serializers.IntegerField(read_only=True)
    estimated_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    effective_cost = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    spent_cost = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    remaining_cost = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    parts_bought_count = serializers.IntegerField(read_only=True)
    parts_count = serializers.IntegerField(read_only=True)
    products = RoomPlanProductSerializer(many=True, read_only=True)

    class Meta:
        model = RoomPlanItem
        fields = [
            "id", "room_id", "assigned_to_person_ids", "title", "plan_mode", "item_type",
            "status", "priority", "description", "quantity", "estimated_unit_cost",
            "estimated_total", "actual_cost", "effective_cost", "spent_cost",
            "remaining_cost", "parts_bought_count", "parts_count", "notes", "position",
            "completed_at", "visibility", "products", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "room_id", "estimated_total", "effective_cost", "spent_cost",
            "remaining_cost", "parts_bought_count", "parts_count", "completed_at",
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
        read_only_fields = [
            "id", "name", "provider", "premium_amount", "billing_cycle",
            "next_renewal_at", "recurrence_rule", "is_active", "notes", "visibility",
            "solace_bill_ref", "created_at", "updated_at",
        ]

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
        read_only_fields = [
            "id", "name", "provider", "amount", "billing_cycle", "next_due_at",
            "recurrence_rule", "is_active", "notes", "visibility", "solace_bill_ref",
            "created_at", "updated_at",
        ]

    def validate_name(self, value: str) -> str:
        return _non_blank(value)


class UtilityBillSerializer(serializers.ModelSerializer):
    """A metered bill, plus the per-day figures that make two periods comparable."""

    unit_label = serializers.CharField(read_only=True)
    days = serializers.IntegerField(read_only=True)
    daily_usage = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)
    daily_cost = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    unit_cost = serializers.DecimalField(
        max_digits=12, decimal_places=4, read_only=True, allow_null=True
    )

    class Meta:
        model = UtilityBill
        fields = [
            "id", "utility_type", "provider", "period_start", "period_end",
            "usage_amount", "usage_unit", "unit_label", "amount", "is_estimated",
            "notes", "days", "daily_usage", "daily_cost", "unit_cost", "visibility",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "unit_label", "days", "daily_usage", "daily_cost", "unit_cost",
            "created_at", "updated_at",
        ]

    def validate(self, attrs: dict) -> dict:
        # On a PATCH only the changed dates arrive, so fall back to what is already stored —
        # otherwise moving one end of the period would skip the check entirely.
        start = attrs.get("period_start") or getattr(self.instance, "period_start", None)
        end = attrs.get("period_end") or getattr(self.instance, "period_end", None)
        if start and end and end < start:
            raise serializers.ValidationError(
                {"period_end": "The period must end on or after it starts."}
            )
        return attrs


class UtilityChangeSerializer(serializers.Serializer):
    """How the latest period compares with another one — the reason to look at all."""

    label = serializers.CharField()
    usage_percent = serializers.DecimalField(
        max_digits=8, decimal_places=1, allow_null=True
    )
    cost_percent = serializers.DecimalField(max_digits=8, decimal_places=1, allow_null=True)


class UtilityPeriodSerializer(serializers.Serializer):
    """One plotted point: a billing period reduced to what a chart needs."""

    id = serializers.IntegerField()
    label = serializers.CharField()
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    days = serializers.IntegerField()
    usage_amount = serializers.DecimalField(max_digits=14, decimal_places=3)
    daily_usage = serializers.DecimalField(max_digits=14, decimal_places=3)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    daily_cost = serializers.DecimalField(max_digits=12, decimal_places=2)
    unit_cost = serializers.DecimalField(
        max_digits=12, decimal_places=4, allow_null=True
    )
    is_estimated = serializers.BooleanField()


class UtilitySeriesSerializer(serializers.Serializer):
    """Everything the usage screen shows for one utility."""

    utility_type = serializers.CharField()
    label = serializers.CharField()
    unit_label = serializers.CharField()
    bill_count = serializers.IntegerField()
    total_usage = serializers.DecimalField(max_digits=16, decimal_places=3)
    total_cost = serializers.DecimalField(max_digits=14, decimal_places=2)
    average_daily_usage = serializers.DecimalField(max_digits=14, decimal_places=3)
    average_daily_cost = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_unit_cost = serializers.DecimalField(
        max_digits=12, decimal_places=4, allow_null=True
    )
    latest = UtilityPeriodSerializer(allow_null=True)
    changes = UtilityChangeSerializer(many=True)
    periods = UtilityPeriodSerializer(many=True)


class PoolSerializer(serializers.ModelSerializer):
    room_id = serializers.IntegerField(required=False, allow_null=True)
    has_salt_cell = serializers.BooleanField(read_only=True)

    class Meta:
        model = Pool
        fields = [
            "id", "room_id", "name", "kind", "sanitiser", "surface", "filter_type",
            "volume_litres", "is_indoor", "equipment_notes", "notes", "is_active",
            "has_salt_cell", "visibility", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "has_salt_cell", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        return _non_blank(value)


class WaterTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaterTest
        fields = [
            "id", "pool_id", "tested_at", "free_chlorine", "ph", "total_alkalinity",
            "calcium_hardness", "cyanuric_acid", "salt", "water_temp_c", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "pool_id", "created_at", "updated_at"]

    def validate_ph(self, value):
        # Outside 0–14 is a typo, and a stored typo quietly makes the guidance nonsense.
        if value is not None and not (Decimal("0") <= value <= Decimal("14")):
            raise serializers.ValidationError("pH is measured from 0 to 14.")
        return value


class PoolReadingAssessmentSerializer(serializers.Serializer):
    """One assessed reading: what it was, whether it is in band, and what to do about it."""

    status = serializers.CharField()
    label = serializers.CharField()
    unit = serializers.CharField()
    value = serializers.DecimalField(max_digits=10, decimal_places=2)
    min = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    max = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    advice = serializers.CharField(allow_blank=True)
    why = serializers.CharField(allow_blank=True)


class PoolTargetSerializer(serializers.Serializer):
    label = serializers.CharField()
    unit = serializers.CharField()
    min = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    max = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    why = serializers.CharField(allow_blank=True)
    low = serializers.CharField(allow_blank=True)
    high = serializers.CharField(allow_blank=True)
