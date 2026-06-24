"""scheduling serializers."""
from __future__ import annotations

from rest_framework import serializers

from apps.scheduling.models import CalendarEvent


class CalendarEventSerializer(serializers.ModelSerializer):
    is_synced = serializers.BooleanField(read_only=True)

    class Meta:
        model = CalendarEvent
        fields = [
            "id",
            "title",
            "description",
            "start_at",
            "end_at",
            "is_all_day",
            "timezone",
            "recurrence_rule",
            "source_node_id",
            "source_record_type",
            "source_record_id",
            "assigned_to_person_id",
            "colour",
            "location",
            "visibility",
            "sensitivity",
            "is_synced",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "source_node_id",
            "source_record_type",
            "source_record_id",
            "is_synced",
            "created_at",
            "updated_at",
        ]


class CalendarEventWriteSerializer(serializers.ModelSerializer):
    """Accepts writes for standalone events only. Synced events are immutable via API."""

    class Meta:
        model = CalendarEvent
        fields = [
            "title",
            "description",
            "start_at",
            "end_at",
            "is_all_day",
            "timezone",
            "recurrence_rule",
            "assigned_to_person_id",
            "colour",
            "location",
            "visibility",
            "sensitivity",
        ]

    def validate_title(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Title may not be blank.")
        return value
