"""backups serializers."""
from rest_framework import serializers

from apps.backups.models import Backup


class BackupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Backup
        fields = [
            "id", "label", "status",
            "db_checksum", "media_checksum",
            "size_bytes", "error_message",
            "created_at", "updated_at",
        ]
        read_only_fields = fields
