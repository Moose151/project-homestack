"""education serializers."""
from __future__ import annotations

from rest_framework import serializers

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
            "assigned_to_person_id", "due_at", "is_all_day", "status", "priority", "weight",
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


class EducationEventSerializer(serializers.ModelSerializer):
    course_id = serializers.IntegerField(required=False, allow_null=True)
    institution_id = serializers.IntegerField(required=False, allow_null=True)
    assigned_to_person_id = serializers.IntegerField(required=False, allow_null=True)
    course_name = serializers.CharField(source="course.name", read_only=True, default="")
    course_code = serializers.CharField(source="course.code", read_only=True, default="")
    institution_name = serializers.CharField(source="institution.name", read_only=True, default="")

    class Meta:
        model = EducationEvent
        fields = [
            "id", "title", "event_type", "course_id", "course_name", "course_code",
            "institution_id", "institution_name", "assigned_to_person_id",
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
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else ""


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
