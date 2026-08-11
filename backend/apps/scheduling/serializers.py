"""scheduling serializers."""
from __future__ import annotations

from rest_framework import serializers

from apps.core.serializers import AssigneeSerializerMixin

from apps.people.models import Person
from apps.accounts.models import User
from apps.scheduling.models import CalendarEvent, RotatingSchedule, RotatingScheduleException


class CalendarEventSerializer(AssigneeSerializerMixin, serializers.ModelSerializer):
    is_synced = serializers.BooleanField(read_only=True)
    source_node = serializers.SerializerMethodField()
    hidden_from_user_ids = serializers.PrimaryKeyRelatedField(source="hidden_from_users", many=True, read_only=True)

    class Meta:
        model = CalendarEvent
        fields = [
            "id",
            "title",
            "event_kind",
            "description",
            "start_at",
            "end_at",
            "is_all_day",
            "timezone",
            "recurrence_rule",
            "source_node",
            "source_node_id",
            "source_record_type",
            "source_record_id",
            "assigned_to_person_ids",
            "hidden_from_user_ids",
            "colour",
            "location",
            "provider",
            "contact",
            "visibility",
            "sensitivity",
            "is_synced",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "source_node",
            "source_node_id",
            "source_record_type",
            "source_record_id",
            "is_synced",
            "created_at",
            "updated_at",
        ]

    def get_source_node(self, obj) -> str | None:
        """The source node's key (e.g. 'atlas') for display/filtering, or None for standalone."""
        return obj.source_node.key if obj.source_node_id else None


class CalendarEventWriteSerializer(AssigneeSerializerMixin, serializers.ModelSerializer):
    """Accepts writes for standalone events only. Synced events are immutable via API."""
    hidden_from_user_ids = serializers.PrimaryKeyRelatedField(source="hidden_from_users", queryset=User.objects.all(), many=True, required=False)

    class Meta:
        model = CalendarEvent
        fields = [
            "title",
            "event_kind",
            "description",
            "start_at",
            "end_at",
            "is_all_day",
            "timezone",
            "recurrence_rule",
            "assigned_to_person_ids",
            "hidden_from_user_ids",
            "colour",
            "location",
            "provider",
            "contact",
            "visibility",
            "sensitivity",
        ]

    def validate_title(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Title may not be blank.")
        return value


class RotatingScheduleSerializer(serializers.ModelSerializer):
    cycle_length = serializers.IntegerField(read_only=True)
    people = serializers.SerializerMethodField()

    class Meta:
        model = RotatingSchedule
        fields = [
            "id", "title", "primary_label", "secondary_label", "anchor_date",
            "cycle_pattern", "cycle_length", "primary_colour", "secondary_colour",
            "people", "visibility", "is_active", "created_at", "updated_at",
        ]

    def get_people(self, obj) -> list[dict]:
        return [
            {
                "id": person.id,
                "display_name": person.display_name,
                "preferred_name": person.preferred_name,
                "colour": person.colour,
                "profile_type": person.profile_type,
            }
            for person in obj.people.all()
        ]


class RotatingScheduleWriteSerializer(serializers.ModelSerializer):
    person_ids = serializers.PrimaryKeyRelatedField(
        source="people",
        queryset=Person.objects.all(),
        many=True,
        required=False,
    )

    class Meta:
        model = RotatingSchedule
        fields = [
            "title", "primary_label", "secondary_label", "anchor_date",
            "cycle_pattern", "primary_colour", "secondary_colour", "person_ids",
            "visibility", "is_active",
        ]

    def validate_cycle_pattern(self, value: str) -> str:
        pattern = value.strip().upper()
        if not 2 <= len(pattern) <= 62 or any(char not in {"P", "S"} for char in pattern):
            raise serializers.ValidationError(
                "Use between 2 and 62 days containing only P (primary) and S (secondary)."
            )
        if "P" not in pattern or "S" not in pattern:
            raise serializers.ValidationError("The rotation must contain both states.")
        return pattern

    def validate(self, attrs):
        for field in ("title", "primary_label", "secondary_label"):
            if field in attrs and not attrs[field].strip():
                raise serializers.ValidationError({field: "This field may not be blank."})
        return attrs


class RotatingScheduleExceptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RotatingScheduleException
        fields = ["date", "state", "note", "created_at", "updated_at"]
        read_only_fields = ["date", "created_at", "updated_at"]


class RotatingScheduleExceptionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RotatingScheduleException
        fields = ["state", "note"]
