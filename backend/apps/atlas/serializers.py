"""atlas serializers."""
from __future__ import annotations

from rest_framework import serializers

from apps.atlas.models import AtlasList, AtlasListItem, AtlasNote, AtlasReminder


class AtlasNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AtlasNote
        fields = [
            "id", "title", "body", "visibility", "sensitivity",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_title(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Title may not be blank.")
        return value


class AtlasListItemSerializer(serializers.ModelSerializer):
    is_complete = serializers.BooleanField(read_only=True)

    class Meta:
        model = AtlasListItem
        fields = [
            "id", "atlas_list_id", "title", "notes", "quantity", "position", "due_at",
            "assigned_to_person_id",
            "completed_at", "completed_by_id", "is_complete",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "atlas_list_id", "completed_at", "completed_by_id", "is_complete", "created_at", "updated_at"]


class AtlasListSerializer(serializers.ModelSerializer):
    items = AtlasListItemSerializer(many=True, read_only=True)

    class Meta:
        model = AtlasList
        fields = [
            "id", "title", "list_type", "visibility",
            "items", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "items", "created_at", "updated_at"]

    def validate_title(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Title may not be blank.")
        return value


class AtlasListWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AtlasList
        fields = ["title", "list_type", "visibility"]

    def validate_title(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Title may not be blank.")
        return value


class AtlasListItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AtlasListItem
        fields = ["title", "notes", "quantity", "position", "due_at", "assigned_to_person_id"]

    def validate_title(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Title may not be blank.")
        return value


class AtlasReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = AtlasReminder
        fields = [
            "id", "title", "body", "due_at", "is_all_day", "recurrence_rule",
            "calendar_event_id", "visibility", "sensitivity",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "calendar_event_id", "created_at", "updated_at"]

    def validate_title(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Title may not be blank.")
        return value
