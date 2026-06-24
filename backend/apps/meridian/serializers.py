"""meridian serializers."""
from __future__ import annotations

from rest_framework import serializers

from apps.meridian.models import (
    MeridianCategory,
    MeridianPointsEntry,
    MeridianReward,
    MeridianRewardRequest,
    MeridianTask,
)


class MeridianCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MeridianCategory
        fields = ["id", "name", "colour", "icon", "position", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Name may not be blank.")
        return value


class MeridianTaskSerializer(serializers.ModelSerializer):
    is_complete = serializers.BooleanField(read_only=True)

    class Meta:
        model = MeridianTask
        fields = [
            "id", "title", "description", "points",
            "category_id", "assigned_to_person_id",
            "status", "is_hot", "is_complete",
            "due_at", "recurrence_rule", "calendar_event_id",
            "completed_at", "completed_by_person_id",
            "approved_at", "approved_by_id", "rejection_reason",
            "visibility", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "is_complete", "calendar_event_id",
            "completed_at", "completed_by_person_id",
            "approved_at", "approved_by_id", "rejection_reason",
            "created_at", "updated_at",
        ]


class MeridianTaskWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeridianTask
        fields = [
            "title", "description", "points", "category_id",
            "assigned_to_person_id", "is_hot",
            "due_at", "recurrence_rule", "visibility",
        ]

    def validate_title(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Title may not be blank.")
        return value


class MeridianRewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeridianReward
        fields = [
            "id", "name", "description", "cost_points",
            "icon", "colour", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Name may not be blank.")
        return value


class MeridianRewardRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeridianRewardRequest
        fields = [
            "id", "reward_id", "requested_by_person_id", "status",
            "points_spent", "approved_at", "approved_by_id",
            "rejection_reason", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "points_spent", "approved_at",
            "approved_by_id", "rejection_reason", "created_at", "updated_at",
        ]


class MeridianPointsEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = MeridianPointsEntry
        fields = [
            "id", "person_id", "points", "reason",
            "source_task_id", "source_reward_request_id", "created_at",
        ]
        read_only_fields = fields


class PointsSummarySerializer(serializers.Serializer):
    """Per-person points balance (not a model — assembled in selectors)."""

    person_id = serializers.IntegerField()
    display_name = serializers.CharField()
    balance = serializers.IntegerField()
