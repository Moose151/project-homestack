"""education services — write operations (Coding Standards §6).

Assessments (due dates) and class sessions (weekly timetable) mirror to the shared
calendar via the scheduling helper only (D7) — never CalendarEvent.objects directly.
"""
from __future__ import annotations

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.education.models import (
    EducationAssessment,
    EducationClassSession,
    EducationCourse,
    EducationInstitution,
)
from apps.scheduling.helpers import delete_event_for, sync_event_for

# ---------------------------------------------------------------------------
# Institutions
# ---------------------------------------------------------------------------

_INSTITUTION_FIELDS = {"name", "institution_type", "location", "notes", "visibility"}


def create_institution(acting_user: User, **data) -> EducationInstitution:
    obj = EducationInstitution(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    return obj


def update_institution(acting_user: User, obj: EducationInstitution, **data) -> EducationInstitution:
    for key, val in data.items():
        if key in _INSTITUTION_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    return obj


def delete_institution(acting_user: User, obj: EducationInstitution) -> None:
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


# ---------------------------------------------------------------------------
# Courses
# ---------------------------------------------------------------------------

_COURSE_FIELDS = {
    "name", "code", "institution_id", "student_id", "teacher", "start_date",
    "end_date", "colour", "description", "is_archived", "visibility",
}


def create_course(acting_user: User, **data) -> EducationCourse:
    obj = EducationCourse(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    return obj


def update_course(acting_user: User, obj: EducationCourse, **data) -> EducationCourse:
    for key, val in data.items():
        if key in _COURSE_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    return obj


def delete_course(acting_user: User, obj: EducationCourse) -> None:
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


# ---------------------------------------------------------------------------
# Assessments
# ---------------------------------------------------------------------------

_ASSESSMENT_FIELDS = {
    "title", "assessment_type", "course_id", "assigned_to_person_id", "due_at", "is_all_day",
    "status", "priority", "weight", "description", "visibility", "sensitivity",
}


def create_assessment(acting_user: User, **data) -> EducationAssessment:
    obj = EducationAssessment(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    sync_event_for(obj)
    return obj


def update_assessment(acting_user: User, obj: EducationAssessment, **data) -> EducationAssessment:
    for key, val in data.items():
        if key in _ASSESSMENT_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    sync_event_for(obj)
    return obj


def delete_assessment(acting_user: User, obj: EducationAssessment) -> None:
    delete_event_for(obj)
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


# ---------------------------------------------------------------------------
# Class sessions (timetable)
# ---------------------------------------------------------------------------

_CLASS_FIELDS = {
    "title", "course_id", "student_id", "location", "start_at", "end_at",
    "recurrence_rule", "visibility",
}


def create_class_session(acting_user: User, **data) -> EducationClassSession:
    obj = EducationClassSession(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    sync_event_for(obj)
    return obj


def update_class_session(acting_user: User, obj: EducationClassSession, **data) -> EducationClassSession:
    for key, val in data.items():
        if key in _CLASS_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    sync_event_for(obj)
    return obj


def delete_class_session(acting_user: User, obj: EducationClassSession) -> None:
    delete_event_for(obj)
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()
