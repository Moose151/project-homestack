"""education serializers."""
from __future__ import annotations

from rest_framework import serializers

from apps.education.models import (
    EducationAssessment,
    EducationClassSession,
    EducationCourse,
    EducationInstitution,
)


def _non_blank(value: str) -> str:
    if not value.strip():
        raise serializers.ValidationError("This field may not be blank.")
    return value


class EducationInstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationInstitution
        fields = [
            "id", "name", "institution_type", "location", "notes", "visibility",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        return _non_blank(value)


class EducationCourseSerializer(serializers.ModelSerializer):
    # DRF treats a bare `<fk>_id` listed in `fields` as read-only; declare them explicitly so
    # they are writable (source defaults to the concrete attname, so they also read back).
    institution_id = serializers.IntegerField(required=False, allow_null=True)
    student_id = serializers.IntegerField(required=False, allow_null=True)
    institution_name = serializers.CharField(source="institution.name", read_only=True, default="")
    student_name = serializers.CharField(source="student.display_name", read_only=True, default="")

    class Meta:
        model = EducationCourse
        fields = [
            "id", "name", "code", "institution_id", "institution_name",
            "student_id", "student_name", "teacher", "start_date", "end_date",
            "colour", "description", "is_archived", "visibility",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "institution_name", "student_name", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        return _non_blank(value)


class EducationAssessmentSerializer(serializers.ModelSerializer):
    course_id = serializers.IntegerField(required=False, allow_null=True)
    assigned_to_person_id = serializers.IntegerField(required=False, allow_null=True)
    course_name = serializers.CharField(source="course.name", read_only=True, default="")
    course_code = serializers.CharField(source="course.code", read_only=True, default="")
    is_complete = serializers.BooleanField(read_only=True)

    class Meta:
        model = EducationAssessment
        fields = [
            "id", "title", "assessment_type", "course_id", "course_name", "course_code",
            "assigned_to_person_id", "due_at", "status", "priority", "weight",
            "description", "is_complete", "calendar_event_id", "visibility", "sensitivity",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "course_name", "course_code", "is_complete", "calendar_event_id",
            "created_at", "updated_at",
        ]

    def validate_title(self, value: str) -> str:
        return _non_blank(value)


class EducationClassSessionSerializer(serializers.ModelSerializer):
    course_id = serializers.IntegerField(required=False, allow_null=True)
    student_id = serializers.IntegerField(required=False, allow_null=True)
    course_name = serializers.CharField(source="course.name", read_only=True, default="")
    course_code = serializers.CharField(source="course.code", read_only=True, default="")
    display_title = serializers.CharField(read_only=True)

    class Meta:
        model = EducationClassSession
        fields = [
            "id", "title", "display_title", "course_id", "course_name", "course_code",
            "student_id", "location", "start_at", "end_at", "recurrence_rule",
            "calendar_event_id", "visibility", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "display_title", "course_name", "course_code", "calendar_event_id",
            "created_at", "updated_at",
        ]

    def validate(self, attrs):
        if self.instance is None and not attrs.get("start_at"):
            raise serializers.ValidationError({"start_at": "A start time is required."})
        return attrs
