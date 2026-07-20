"""pets serializers."""
from __future__ import annotations

from rest_framework import serializers

from apps.pets.models import Pet, PetAppointment, PetTreatment


def _non_blank(value: str) -> str:
    if not value.strip():
        raise serializers.ValidationError("This field may not be blank.")
    return value


class PetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pet
        fields = [
            "id", "name", "species", "breed", "avatar", "colour",
            "date_of_birth", "adoption_date", "notes", "vet_name", "vet_phone",
            "microchip_number", "insurance_provider", "insurance_policy_number",
            "food_notes", "is_archived", "visibility", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        return _non_blank(value)


class PetTreatmentSerializer(serializers.ModelSerializer):
    # DRF treats a bare `<fk>_id` in `fields` as read-only; declare it so writes land.
    pet_id = serializers.IntegerField()
    pet_name = serializers.CharField(source="pet.name", read_only=True, default="")
    display_name = serializers.CharField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = PetTreatment
        fields = [
            "id", "pet_id", "pet_name", "treatment_type", "name", "display_name",
            "last_done_at", "next_due_at", "recurrence_rule", "notes", "is_overdue",
            "calendar_event_id", "visibility", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "pet_name", "display_name", "is_overdue", "calendar_event_id",
            "created_at", "updated_at",
        ]


class PetAppointmentSerializer(serializers.ModelSerializer):
    pet_id = serializers.IntegerField()
    pet_name = serializers.CharField(source="pet.name", read_only=True, default="")
    display_title = serializers.CharField(read_only=True)

    class Meta:
        model = PetAppointment
        fields = [
            "id", "pet_id", "pet_name", "title", "display_title", "provider", "location",
            "start_at", "end_at", "notes", "calendar_event_id", "visibility",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "pet_name", "display_title", "calendar_event_id", "created_at", "updated_at",
        ]

    def validate(self, attrs):
        if not self.partial and not attrs.get("start_at"):
            raise serializers.ValidationError({"start_at": "A start time is required."})
        return attrs
