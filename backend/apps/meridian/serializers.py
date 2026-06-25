"""meridian serializers."""
from __future__ import annotations

from rest_framework import serializers

from apps.meridian.models import (
    MeridianCategory,
    MeridianGroupGoal,
    MeridianPointsEntry,
    MeridianReward,
    MeridianRewardRequest,
    MeridianRoutine,
    MeridianTask,
    MeridianWishlistItem,
    MeridianWishlistRequest,
)


class MeridianCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MeridianCategory
        fields = ["id", "name", "kind", "colour", "icon", "position", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Name may not be blank.")
        return value


class MeridianTaskSerializer(serializers.ModelSerializer):
    is_complete = serializers.BooleanField(read_only=True)
    award_value = serializers.IntegerField(read_only=True)

    class Meta:
        model = MeridianTask
        fields = [
            "id", "title", "description", "points",
            "category_id", "assigned_to_person_id",
            "status", "is_hot", "is_complete", "award_value",
            "hot_bonus_points", "hot_label",
            "completion_behavior", "completion_scope", "availability_window",
            "is_active", "is_archived",
            "due_at", "recurrence_rule", "calendar_event_id",
            "completed_at", "completed_by_person_id",
            "approved_at", "approved_by_id", "rejection_reason",
            "visibility", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "is_complete", "award_value", "calendar_event_id",
            "completed_at", "completed_by_person_id",
            "approved_at", "approved_by_id", "rejection_reason",
            "created_at", "updated_at",
        ]


class MeridianTaskWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeridianTask
        fields = [
            "title", "description", "points", "category_id",
            "assigned_to_person_id", "is_hot", "hot_bonus_points", "hot_label",
            "completion_behavior", "completion_scope", "availability_window",
            "is_active", "is_archived",
            "due_at", "recurrence_rule", "visibility",
        ]

    def validate_title(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Title may not be blank.")
        return value


class MeridianRoutineSerializer(serializers.ModelSerializer):
    # Per-person context, supplied by the view for the requesting person (optional).
    streak = serializers.IntegerField(read_only=True, required=False)
    done_today = serializers.BooleanField(read_only=True, required=False)

    class Meta:
        model = MeridianRoutine
        fields = [
            "id", "title", "description", "points", "assigned_to_person_id",
            "is_active", "visibility", "streak", "done_today",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "streak", "done_today", "created_at", "updated_at"]

    def validate_title(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Title may not be blank.")
        return value


class MeridianRewardSerializer(serializers.ModelSerializer):
    remaining_stock = serializers.SerializerMethodField()

    class Meta:
        model = MeridianReward
        fields = [
            "id", "name", "description", "cost_points",
            "icon", "colour", "image_url", "is_active", "is_archived",
            "price_estimate", "store_url",
            "quantity", "allow_multiple_in_cart", "disappear_when_empty",
            "daily_limit_per_user", "remaining_stock",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "remaining_stock", "created_at", "updated_at"]

    def get_remaining_stock(self, obj) -> int | None:
        return obj.remaining_stock()

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


class MeridianGroupGoalSerializer(serializers.ModelSerializer):
    total_contributed = serializers.SerializerMethodField()
    remaining_points = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = MeridianGroupGoal
        fields = [
            "id", "title", "description", "target_points",
            "price_estimate", "store_url", "image_url", "status", "is_active",
            "total_contributed", "remaining_points", "progress_percentage",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "total_contributed", "remaining_points",
            "progress_percentage", "created_at", "updated_at",
        ]

    def get_total_contributed(self, obj) -> int:
        return obj.total_contributed()

    def get_remaining_points(self, obj) -> int:
        return obj.remaining_points()

    def get_progress_percentage(self, obj) -> int:
        return obj.progress_percentage()

    def validate_title(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Title may not be blank.")
        return value


class MeridianWishlistRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeridianWishlistRequest
        fields = [
            "id", "person_id", "requested_name", "requested_description",
            "status", "rejection_reason", "reviewed_at", "reviewed_by_id", "created_at",
        ]
        read_only_fields = [
            "id", "status", "rejection_reason", "reviewed_at", "reviewed_by_id", "created_at",
        ]

    def validate_requested_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Name may not be blank.")
        return value


class MeridianWishlistItemSerializer(serializers.ModelSerializer):
    total_saved = serializers.SerializerMethodField()
    remaining_points = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = MeridianWishlistItem
        fields = [
            "id", "person_id", "name", "description", "point_cost",
            "status", "is_active", "price_estimate", "store_url", "image_url",
            "total_saved", "remaining_points", "progress_percentage",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "total_saved", "remaining_points",
            "progress_percentage", "created_at", "updated_at",
        ]

    def get_total_saved(self, obj) -> int:
        return obj.total_saved()

    def get_remaining_points(self, obj) -> int:
        return obj.remaining_points()

    def get_progress_percentage(self, obj) -> int:
        return obj.progress_percentage()


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
