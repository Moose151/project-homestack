"""core serializers — Household read/write."""
from rest_framework import serializers

from apps.core.models import Household


_CALENDAR_FIELDS = ["calendar_default_view", "calendar_week_start", "calendar_time_format"]


class HouseholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Household
        fields = [
            "id", "name", "slug", "timezone", "default_locale", "family_colour",
            *_CALENDAR_FIELDS, "created_at", "updated_at",
        ]
        read_only_fields = fields


class HouseholdWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Household
        fields = ["name", "timezone", "default_locale", "family_colour", *_CALENDAR_FIELDS]
