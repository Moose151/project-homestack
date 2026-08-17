"""scheduling serializers."""
from __future__ import annotations

from rest_framework import serializers

from apps.core.serializers import AssigneeSerializerMixin

from apps.people.models import Person
from apps.accounts.models import User
from apps.scheduling.models import CalendarEvent, CalendarSource, RotatingSchedule, RotatingScheduleException


class CalendarEventSerializer(AssigneeSerializerMixin, serializers.ModelSerializer):
    is_synced = serializers.BooleanField(read_only=True)
    # Source-managed entries are read-only locally: editing one would be overwritten by the very
    # next sync, so the client is told plainly rather than discovering it later.
    is_source_managed = serializers.BooleanField(read_only=True)
    calendar_source_name = serializers.SerializerMethodField()
    calendar_source_category = serializers.SerializerMethodField()
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
            "calendar_source_id",
            "calendar_source_name",
            "calendar_source_category",
            "is_source_managed",
            "is_range",
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

    def get_calendar_source_name(self, obj) -> str:
        return obj.calendar_source.name if obj.calendar_source_id else ""

    def get_calendar_source_category(self, obj) -> str:
        return obj.calendar_source.category if obj.calendar_source_id else ""


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


class CalendarSourceSerializer(serializers.ModelSerializer):
    """What the household sees about a source. Internal module names stay out of it."""

    type_label = serializers.SerializerMethodField()
    can_sync = serializers.SerializerMethodField()
    event_count = serializers.SerializerMethodField()

    class Meta:
        model = CalendarSource
        fields = [
            "id", "name", "kind", "category", "type_label", "is_enabled", "colour",
            "url", "settings_json", "show_on_calendar", "show_in_upcoming",
            "notifications_enabled", "last_sync_at", "last_success_at", "sync_status",
            "sync_error", "can_sync", "event_count", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "kind", "type_label", "last_sync_at", "last_success_at", "sync_status",
            "sync_error", "can_sync", "event_count", "created_at", "updated_at",
        ]

    def get_type_label(self, obj) -> str:
        from apps.scheduling.sources.registry import PROVIDERS
        entry = PROVIDERS.get((obj.kind, obj.provider))
        return entry["label"] if entry else obj.get_kind_display()

    def get_can_sync(self, obj) -> bool:
        from apps.scheduling.sources.sync import spec_syncs
        return spec_syncs(obj)

    def get_event_count(self, obj) -> int:
        return obj.events.count()


class CalendarSourceWriteSerializer(serializers.Serializer):
    """Creation/update input. `kind`/`provider` must exist in the registry."""

    name = serializers.CharField(max_length=120, required=False)
    kind = serializers.CharField(max_length=20, required=False)
    provider = serializers.CharField(max_length=40, required=False)
    is_enabled = serializers.BooleanField(required=False)
    colour = serializers.CharField(max_length=7, required=False, allow_blank=True)
    category = serializers.CharField(max_length=40, required=False, allow_blank=True)
    url = serializers.CharField(max_length=500, required=False, allow_blank=True)
    settings_json = serializers.DictField(required=False)
    show_on_calendar = serializers.BooleanField(required=False)
    show_in_upcoming = serializers.BooleanField(required=False)
    notifications_enabled = serializers.BooleanField(required=False)
    # One-time import only: the file's contents, posted rather than fetched.
    ics_text = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)
