"""education serializers."""
from __future__ import annotations

from datetime import timedelta

from django.urls import reverse
from rest_framework import serializers

from apps.core.serializers import AssigneeSerializerMixin
from apps.education import services

from apps.education.models import (
    EducationAcademicProfile,
    EducationAssessment,
    EducationAssessmentFile,
    EducationAssessmentNote,
    EducationClassSession,
    EducationCourse,
    EducationEvent,
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
            "credit_value", "is_completed",
            "colour", "description", "is_archived", "visibility",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "institution_name", "student_name", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        return _non_blank(value)


class EducationAssessmentSerializer(AssigneeSerializerMixin, serializers.ModelSerializer):
    course_id = serializers.IntegerField(required=False, allow_null=True)
    course_name = serializers.CharField(source="course.name", read_only=True, default="")
    course_code = serializers.CharField(source="course.code", read_only=True, default="")
    is_complete = serializers.BooleanField(read_only=True)

    class Meta:
        model = EducationAssessment
        fields = [
            "id", "title", "assessment_type", "course_id", "course_name", "course_code",
            "assigned_to_person_ids", "due_at", "is_all_day", "status", "priority", "weight",
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

    # --- How a repeating class is described on the way in (write-only) ---
    # A class is entered as "first class, how long it runs, how often, last class" and the server
    # generates one real session per occurrence. `end_at` is still the stored truth, so an
    # existing caller sending start_at/end_at directly keeps working.
    duration_minutes = serializers.IntegerField(
        write_only=True, required=False, min_value=5, max_value=24 * 60,
    )
    repeat = serializers.ChoiceField(
        write_only=True, required=False, allow_blank=True, default="",
        choices=[(key, key) for key in services.CLASS_REPEAT_INTERVALS],
    )
    repeat_until = serializers.DateField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = EducationClassSession
        fields = [
            "id", "title", "display_title", "course_id", "course_name", "course_code",
            "student_id", "location", "start_at", "end_at", "recurrence_rule",
            "series_key", "calendar_event_id", "visibility", "created_at", "updated_at",
            "duration_minutes", "repeat", "repeat_until",
        ]
        read_only_fields = [
            "id", "display_title", "course_name", "course_code", "calendar_event_id",
            "series_key", "created_at", "updated_at",
        ]

    def validate(self, attrs):
        if self.instance is None and not attrs.get("start_at"):
            raise serializers.ValidationError({"start_at": "A start time is required."})
        # A duration is the friendlier way to say the same thing as end_at, so fold it in here
        # and let the service deal only in start/end.
        duration = attrs.pop("duration_minutes", None)
        if duration is not None and attrs.get("start_at"):
            attrs["end_at"] = attrs["start_at"] + timedelta(minutes=duration)
        if attrs.get("repeat") and not attrs.get("repeat_until"):
            raise serializers.ValidationError(
                {"repeat_until": "Give the date of the last class in the series."}
            )
        return attrs


class EducationEventSerializer(AssigneeSerializerMixin, serializers.ModelSerializer):
    course_id = serializers.IntegerField(required=False, allow_null=True)
    institution_id = serializers.IntegerField(required=False, allow_null=True)
    course_name = serializers.CharField(source="course.name", read_only=True, default="")
    course_code = serializers.CharField(source="course.code", read_only=True, default="")
    institution_name = serializers.CharField(source="institution.name", read_only=True, default="")

    class Meta:
        model = EducationEvent
        fields = [
            "id", "title", "event_type", "course_id", "course_name", "course_code",
            "institution_id", "institution_name", "assigned_to_person_ids",
            "start_at", "end_at", "is_all_day", "location", "description",
            "recurrence_rule", "calendar_event_id", "visibility",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "course_name", "course_code", "institution_name", "calendar_event_id",
            "created_at", "updated_at",
        ]

    def validate_title(self, value: str) -> str:
        return _non_blank(value)

    def validate(self, attrs):
        if not self.partial and not attrs.get("start_at"):
            raise serializers.ValidationError({"start_at": "A start time is required."})
        return attrs


class AssessmentNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationAssessmentNote
        fields = ["id", "assessment_id", "body", "created_at", "updated_at"]
        read_only_fields = ["id", "assessment_id", "created_at", "updated_at"]

    def validate_body(self, value: str) -> str:
        return _non_blank(value)


class AssessmentFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = EducationAssessmentFile
        fields = [
            "id", "assessment_id", "label", "file_url",
            "original_filename", "file_size", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "assessment_id", "file_url",
            "original_filename", "file_size", "created_at", "updated_at",
        ]

    def get_file_url(self, obj: EducationAssessmentFile) -> str:
        if not obj.file:
            return ""
        # Keep this relative so the browser uses the frontend's same-origin /api proxy;
        # an absolute URL may expose the Docker-only backend hostname after changeOrigin.
        return reverse(
            "education-assessment-file-download",
            args=[obj.assessment_id, obj.id],
        )


class AcademicProfileSerializer(serializers.ModelSerializer):
    person_id = serializers.IntegerField(required=True)
    institution_id = serializers.IntegerField(required=False, allow_null=True)
    institution_name = serializers.CharField(source="institution.name", read_only=True, default="")
    current_credits = serializers.SerializerMethodField()

    class Meta:
        model = EducationAcademicProfile
        fields = [
            "id", "person_id", "institution_id", "institution_name",
            "programme_name", "credits_required", "credits_per_course_default",
            "graduation_year", "notes", "current_credits",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "institution_name", "current_credits", "created_at", "updated_at"]

    def get_current_credits(self, obj: EducationAcademicProfile) -> int:
        return obj.get_current_credits()
