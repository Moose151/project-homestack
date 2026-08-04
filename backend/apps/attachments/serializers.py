"""Attachment API validation and safe metadata representation."""
from __future__ import annotations

from django.conf import settings
from rest_framework import serializers

from apps.attachments.models import Attachment
from apps.nodes.models import Node


class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.PrimaryKeyRelatedField(read_only=True)
    linked_node = serializers.PrimaryKeyRelatedField(
        queryset=Node.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Attachment
        fields = [
            "id",
            "uploaded_by",
            "filename",
            "original_filename",
            "mime_type",
            "file_size",
            "checksum",
            "linked_node",
            "linked_record_type",
            "linked_record_id",
            "visibility",
            "sensitivity",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "uploaded_by",
            "filename",
            "original_filename",
            "mime_type",
            "file_size",
            "checksum",
            "created_at",
            "updated_at",
        ]


class AttachmentUploadSerializer(serializers.Serializer):
    file = serializers.FileField(write_only=True)
    linked_node = serializers.PrimaryKeyRelatedField(
        queryset=Node.objects.all(), required=False, allow_null=True
    )
    linked_record_type = serializers.CharField(
        max_length=150, required=False, allow_blank=True, default=""
    )
    linked_record_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    visibility = serializers.ChoiceField(
        choices=Attachment.Visibility.choices,
        required=False,
        default=Attachment.Visibility.HOUSEHOLD,
    )
    sensitivity = serializers.ChoiceField(
        choices=Attachment.Sensitivity.choices,
        required=False,
        default=Attachment.Sensitivity.NORMAL,
    )

    def validate_file(self, value):
        max_bytes = getattr(settings, "ATTACHMENT_MAX_BYTES", 25 * 1024 * 1024)
        if value.size > max_bytes:
            raise serializers.ValidationError(
                f"File exceeds the {max_bytes // (1024 * 1024) or 1} MB upload limit."
            )
        if value.size <= 0:
            raise serializers.ValidationError("File cannot be empty.")
        return value

    def validate(self, attrs):
        record_type = attrs.get("linked_record_type", "")
        record_id = attrs.get("linked_record_id")
        if bool(record_type) != bool(record_id):
            raise serializers.ValidationError(
                "linked_record_type and linked_record_id must be supplied together."
            )
        return attrs


class AttachmentFilterSerializer(serializers.Serializer):
    linked_node = serializers.PrimaryKeyRelatedField(
        queryset=Node.objects.all(), required=False
    )
    linked_record_type = serializers.CharField(max_length=150, required=False)
    linked_record_id = serializers.IntegerField(required=False, min_value=1)

    def validate(self, attrs):
        record_type = attrs.get("linked_record_type")
        record_id = attrs.get("linked_record_id")
        if (record_type is None) != (record_id is None):
            raise serializers.ValidationError(
                "linked_record_type and linked_record_id filters must be supplied together."
            )
        return attrs
