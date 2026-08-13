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
    """`browser`/`platform` are the secondary technical detail shown under the friendly label.

    The subscription endpoint and keys are deliberately never serialized — they are notification
    infrastructure data, not profile information (docs/32 §13).
    """

    class Meta:
        model = PushDevice
        fields = [
            "id", "label", "label_is_custom", "browser", "platform",
            "user_agent", "last_seen_at", "created_at",
        ]
        read_only_fields = fields


class PushDeviceRegisterSerializer(serializers.Serializer):
    """Shape of the browser's PushSubscription.toJSON(), plus an optional friendly label.

    An omitted label is normal: the server names the device from the User-Agent instead.
    """

    endpoint = serializers.CharField(max_length=500)
    keys = serializers.DictField(child=serializers.CharField())
    label = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")

    def validate_keys(self, value):
        if "p256dh" not in value or "auth" not in value:
            raise serializers.ValidationError("Subscription keys must include p256dh and auth.")
        return value


class PushDeviceCurrentSerializer(serializers.Serializer):
    """Identify the caller's existing browser subscription without serializing its endpoint."""

    endpoint = serializers.CharField(max_length=500)


class PushDeviceRenameSerializer(serializers.Serializer):
    """A blank label is allowed and means "go back to the generated name"."""

    label = serializers.CharField(max_length=120, allow_blank=True)


class HouseholdPushDeviceGroupSerializer(serializers.Serializer):
    """Admin overview row: one household User and their active devices (docs/32 §7)."""

    user_id = serializers.IntegerField(read_only=True)
    user_display_name = serializers.CharField(read_only=True)
    user_role = serializers.CharField(read_only=True)
    devices = PushDeviceSerializer(many=True, read_only=True)
