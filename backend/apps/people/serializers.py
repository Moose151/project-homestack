"""
people serializers — input validation and output representation for Person endpoints.
"""
from rest_framework import serializers

from apps.people.models import Person


class PersonSerializer(serializers.ModelSerializer):
    """Read-only output representation of a Person."""

    # Keep the API's foreign-key representation explicit. The web app (and the
    # canonical data contract) use ``linked_user_id`` to distinguish the login
    # from the Person who represents them around the household.
    linked_user_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Person
        fields = [
            "id",
            "linked_user_id",
            "display_name",
            "preferred_name",
            "avatar",
            "colour",
            "date_of_birth",
            "profile_type",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PersonWriteSerializer(serializers.ModelSerializer):
    """Writable serializer for create and update (linked_user FK is optional)."""

    class Meta:
        model = Person
        fields = [
            "linked_user",
            "display_name",
            "preferred_name",
            "avatar",
            "colour",
            "date_of_birth",
            "profile_type",
            "notes",
        ]

    def validate_display_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("display_name may not be blank.")
        return value
