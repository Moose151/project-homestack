"""audit serializers."""
from rest_framework import serializers

from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_display = serializers.SerializerMethodField()
    node_key = serializers.CharField(source="target_node.key", default=None, read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id", "action", "user", "user_display", "node_key",
            "target_record_type", "target_record_id",
            "ip_address", "metadata_json", "created_at",
        ]
        read_only_fields = fields

    def get_user_display(self, obj) -> str | None:
        return str(obj.user) if obj.user_id else None
