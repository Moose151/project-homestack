"""core serializers — Household read/write."""
from rest_framework import serializers

from apps.core.models import Household


class HouseholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Household
        fields = ["id", "name", "slug", "timezone", "default_locale", "created_at", "updated_at"]
        read_only_fields = fields


class HouseholdWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Household
        fields = ["name", "timezone", "default_locale"]
