"""nodes serializers."""
from rest_framework import serializers

from apps.nodes.models import HouseholdNode, NodeSetting
from apps.nodes.permissions import can_view_node


class NodeSerializer(serializers.ModelSerializer):
    """HouseholdNode with embedded node catalogue fields — the shape the API returns."""

    key = serializers.CharField(source="node.key", read_only=True)
    name = serializers.SerializerMethodField()
    description = serializers.CharField(source="node.description", read_only=True)
    icon = serializers.CharField(source="node.icon", read_only=True)
    is_core = serializers.BooleanField(source="node.is_core", read_only=True)
    supports_kiosk = serializers.BooleanField(source="node.supports_kiosk", read_only=True)
    supports_sensitive_lock = serializers.BooleanField(
        source="node.supports_sensitive_lock", read_only=True
    )
    can_view = serializers.SerializerMethodField()

    class Meta:
        model = HouseholdNode
        fields = [
            "key", "name", "description", "icon", "is_core",
            "supports_kiosk", "supports_sensitive_lock",
            "can_view",
            "is_enabled", "is_hidden", "requires_reauthentication",
            "display_order", "custom_name", "custom_icon",
        ]
        read_only_fields = fields

    def get_name(self, obj) -> str:
        return obj.custom_name or obj.node.name

    def get_can_view(self, obj) -> bool:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return can_view_node(user, obj.node.key)


class NodeSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = NodeSetting
        fields = ["key", "value"]
        read_only_fields = fields

    value = serializers.JSONField(source="value_json")
