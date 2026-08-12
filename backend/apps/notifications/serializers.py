"""notifications serializers."""
from __future__ import annotations

from rest_framework import serializers

from apps.notifications.models import (
    NotificationCategory,
    Notification,
    PushDevice,
    UserNotificationSettings,
)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id", "title", "message", "level", "source_node",
            "action_url", "is_read", "created_at",
        ]
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.Serializer):
    """Reads the plain-dict shape `selectors.list_preferences_for_user` returns."""

    category = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)
    in_app_enabled = serializers.BooleanField()
    push_enabled = serializers.BooleanField()
    mine_only = serializers.BooleanField()
    supports_mine_only = serializers.BooleanField(read_only=True)


class NotificationPreferenceWriteSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=NotificationCategory.choices)
    in_app_enabled = serializers.BooleanField(default=True)
    push_enabled = serializers.BooleanField(default=True)
    mine_only = serializers.BooleanField(default=False)


class UserNotificationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotificationSettings
        fields = ["quiet_start", "quiet_end", "morning_time"]


class PushDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushDevice
        fields = ["id", "label", "user_agent", "last_seen_at", "created_at"]
        read_only_fields = fields


class PushDeviceRegisterSerializer(serializers.Serializer):
    """Shape of the browser's PushSubscription.toJSON(), plus an optional friendly label."""

    endpoint = serializers.CharField(max_length=500)
    keys = serializers.DictField(child=serializers.CharField())
    label = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")

    def validate_keys(self, value):
        if "p256dh" not in value or "auth" not in value:
            raise serializers.ValidationError("Subscription keys must include p256dh and auth.")
        return value
