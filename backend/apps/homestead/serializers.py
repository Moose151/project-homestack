"""homestead serializers."""
from __future__ import annotations

from rest_framework import serializers

from apps.homestead.models import (
    Appliance,
    Improvement,
    MaintenanceTask,
    Property,
    ServiceProvider,
)


def _non_blank(value: str) -> str:
    if not value.strip():
        raise serializers.ValidationError("This field may not be blank.")
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
            "last_done_at", "notes", "is_overdue", "calendar_event_id", "visibility",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "is_overdue", "calendar_event_id", "created_at", "updated_at",
        ]

    def validate_title(self, value: str) -> str:
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
