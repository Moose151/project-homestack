"""hub serializers — widget configuration (M2.5 Workstream A)."""
from __future__ import annotations

from rest_framework import serializers


class CountdownSettingsSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100)
    target_date = serializers.CharField(max_length=10)

    def validate_target_date(self, value: str) -> str:
        from datetime import date

        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise serializers.ValidationError("Use a valid date in YYYY-MM-DD format.") from exc
        return value


class HubWidgetConfigSerializer(serializers.Serializer):
    """Read shape for the Hub configuration screen (catalogue + household + user state)."""

    key = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    source_node = serializers.CharField(allow_null=True)
    source_node_name = serializers.CharField(allow_blank=True)
    supports_kiosk = serializers.BooleanField()
    always_visible = serializers.BooleanField()
    household_enabled = serializers.BooleanField()
    household_order = serializers.IntegerField()
    size = serializers.CharField()
    user_hidden = serializers.BooleanField()
    user_order = serializers.IntegerField(allow_null=True)
    settings = serializers.DictField()


class HouseholdWidgetWriteSerializer(serializers.Serializer):
    is_enabled = serializers.BooleanField(required=False)
    display_order = serializers.IntegerField(required=False)
    size = serializers.ChoiceField(choices=["small", "medium", "large"], required=False)
    settings = CountdownSettingsSerializer(required=False)


class UserWidgetWriteSerializer(serializers.Serializer):
    is_enabled = serializers.BooleanField(required=False)
    display_order = serializers.IntegerField(required=False)


class UserWidgetOrderWriteSerializer(serializers.Serializer):
    keys = serializers.ListField(
        child=serializers.CharField(max_length=50),
        allow_empty=False,
        max_length=100,
    )

    def validate_keys(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Each widget must appear exactly once.")
        return value
