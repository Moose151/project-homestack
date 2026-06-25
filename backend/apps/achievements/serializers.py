"""achievements serializers."""
from __future__ import annotations

from rest_framework import serializers

from apps.achievements.models import Badge, PersonBadge


class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = ["id", "code", "name", "description", "icon", "source", "position"]
        read_only_fields = fields


class PersonBadgeSerializer(serializers.ModelSerializer):
    badge = BadgeSerializer(read_only=True)

    class Meta:
        model = PersonBadge
        fields = ["id", "person_id", "badge", "earned_at", "source"]
        read_only_fields = fields
