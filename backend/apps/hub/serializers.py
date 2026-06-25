"""hub serializers — widget configuration (M2.5 Workstream A)."""
from __future__ import annotations

from rest_framework import serializers


class HubWidgetConfigSerializer(serializers.Serializer):
    """Read shape for the Hub configuration screen (catalogue + household + user state)."""

    key = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    source_node = serializers.CharField(allow_null=True)
    supports_kiosk = serializers.BooleanField()
    household_enabled = serializers.BooleanField()
    household_order = serializers.IntegerField()
    size = serializers.CharField()
    user_hidden = serializers.BooleanField()
    user_order = serializers.IntegerField(allow_null=True)


class HouseholdWidgetWriteSerializer(serializers.Serializer):
    is_enabled = serializers.BooleanField(required=False)
    display_order = serializers.IntegerField(required=False)
    size = serializers.ChoiceField(choices=["small", "medium", "large"], required=False)


class UserWidgetWriteSerializer(serializers.Serializer):
    is_enabled = serializers.BooleanField(required=False)
    display_order = serializers.IntegerField(required=False)
