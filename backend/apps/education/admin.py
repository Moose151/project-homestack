from django.contrib import admin

from apps.education.models import (
    EducationAssessment,
    EducationClassSession,
    EducationCourse,
    EducationEvent,
    EducationInstitution,
)


@admin.register(EducationInstitution)
class EducationInstitutionAdmin(admin.ModelAdmin):
    list_display = ("name", "institution_type", "location")
    search_fields = ("name",)


@admin.register(EducationCourse)
class EducationCourseAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "institution", "student", "is_archived")
    search_fields = ("name", "code", "teacher")
    list_filter = ("is_archived",)


@admin.register(EducationAssessment)
class EducationAssessmentAdmin(admin.ModelAdmin):
    list_display = ("title", "assessment_type", "course", "due_at", "status", "priority")
    search_fields = ("title",)
    list_filter = ("assessment_type", "status", "priority")


@admin.register(EducationClassSession)
class EducationClassSessionAdmin(admin.ModelAdmin):
    list_display = ("display_title", "course", "start_at", "location")
    search_fields = ("title", "location")


@admin.register(EducationEvent)
class EducationEventAdmin(admin.ModelAdmin):
    list_display = ("title", "event_type", "course", "institution", "start_at", "location")
    search_fields = ("title", "location")
    list_filter = ("event_type",)
