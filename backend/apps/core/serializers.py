"""core serializers — Household read/write."""
from rest_framework import serializers

from apps.core.models import Household
from apps.people.models import Person


# Where the household is, for Calendar Sources' jurisdiction lookup (docs/38). Configuration
# only — never an input to permissions.
_LOCATION_FIELDS = ("country", "region", "locality", "postcode")
_CALENDAR_FIELDS = ["calendar_default_view", "calendar_week_start", "calendar_time_format"]


class HouseholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Household
        fields = [
            "id", "name", "slug", "timezone", "default_locale", "family_colour",
            *_LOCATION_FIELDS, *_CALENDAR_FIELDS, "created_at", "updated_at",
        ]
        read_only_fields = fields


class HouseholdWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Household
        fields = [
            "name", "timezone", "default_locale", "family_colour",
            *_LOCATION_FIELDS, *_CALENDAR_FIELDS,
        ]


class AssigneeSerializerMixin(serializers.Serializer):
    """Exposes an assignable record's people as `assigned_to_person_ids`.

    Assignment is a many-to-many (empty = the whole household, one or more = each of those
    people), so the API takes and returns a list of person ids. Declared in one place so a
    to-do, a calendar event and a home job all speak the same shape.

    Declared at class level because DRF's metaclass collects declared fields when the class
    is built — injecting it from get_fields() is too late, and ModelSerializer would first
    try to resolve the name against the model and fail.
    """

    assigned_to_person_ids = serializers.PrimaryKeyRelatedField(
        source="assigned_to_people",
        many=True,
        required=False,
        queryset=Person.objects.all(),  # lazy: no query runs at import time
    )
