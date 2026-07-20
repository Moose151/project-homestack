"""education services — write operations (Coding Standards §6).

Assessments (due dates) and class sessions (weekly timetable) mirror to the shared
calendar via the scheduling helper only (D7) — never CalendarEvent.objects directly.
"""
from __future__ import annotations

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.education import events
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
from apps.notifications import services as notifications
from apps.scheduling.helpers import delete_event_for, sync_event_for


def _notify_assigned(acting_user: User, person_id, *, title: str, message: str, action_url: str = "") -> None:
    """Notify the person an item is assigned to, unless they are the acting user (D12)."""
    if not person_id:
        return
    linked = getattr(acting_user, "person_profile", None)
    if linked is not None and linked.id == person_id:
        return  # don't notify yourself about your own item
    notifications.notify_person_id(
        person_id, title=title, message=message, source_node="education", action_url=action_url,
    )

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
    "end_date", "credit_value", "is_completed", "colour", "description", "is_archived", "visibility",
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
    events.assessment_created(obj.id, obj.household_id)
    _notify_assigned(
        acting_user, obj.assigned_to_person_id,
        title="New assignment",
        message=f"{obj.get_assessment_type_display()}: {obj.title}",
        action_url="/education",
    )
    return obj


def update_assessment(acting_user: User, obj: EducationAssessment, **data) -> EducationAssessment:
    was_complete = obj.is_complete
    for key, val in data.items():
        if key in _ASSESSMENT_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    sync_event_for(obj)
    if obj.is_complete and not was_complete:
        events.assessment_completed(obj.id, obj.household_id)
    return obj


def delete_assessment(acting_user: User, obj: EducationAssessment) -> None:
    delete_event_for(obj)
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


# ---------------------------------------------------------------------------
# Assessment notes
# ---------------------------------------------------------------------------


def create_assessment_note(acting_user: User, assessment: EducationAssessment, body: str) -> EducationAssessmentNote:
    note = EducationAssessmentNote(
        household=get_active_household(),
        created_by=acting_user,
        updated_by=acting_user,
        assessment=assessment,
        body=body,
    )
    note.save()
    return note


def update_assessment_note(acting_user: User, note: EducationAssessmentNote, body: str) -> EducationAssessmentNote:
    note.body = body
    note.updated_by = acting_user
    note.save()
    return note


def delete_assessment_note(acting_user: User, note: EducationAssessmentNote) -> None:
    note.updated_by = acting_user
    note.save(update_fields=["updated_by", "updated_at"])
    note.soft_delete()


# ---------------------------------------------------------------------------
# Assessment files
# ---------------------------------------------------------------------------


def create_assessment_file(
    acting_user: User,
    assessment: EducationAssessment,
    file,
    label: str = "",
) -> EducationAssessmentFile:
    original_filename = getattr(file, "name", "") or ""
    obj = EducationAssessmentFile(
        household=get_active_household(),
        created_by=acting_user,
        updated_by=acting_user,
        assessment=assessment,
        label=label or original_filename,
        original_filename=original_filename,
        file_size=file.size if hasattr(file, "size") else 0,
    )
    obj.save()
    obj.file = file
    obj.save(update_fields=["file"])
    return obj


def delete_assessment_file(acting_user: User, obj: EducationAssessmentFile) -> None:
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
    events.class_session_created(obj.id, obj.household_id)
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


# ---------------------------------------------------------------------------
# Education events (excursions, school events, term dates, milestones)
# ---------------------------------------------------------------------------

_EVENT_FIELDS = {
    "title", "event_type", "course_id", "institution_id", "assigned_to_person_id",
    "start_at", "end_at", "is_all_day", "location", "description", "recurrence_rule", "visibility",
}


def create_event(acting_user: User, **data) -> EducationEvent:
    obj = EducationEvent(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    sync_event_for(obj)
    events.school_event_created(obj.id, obj.household_id)
    _notify_assigned(
        acting_user, obj.assigned_to_person_id,
        title="New education event",
        message=f"{obj.get_event_type_display()}: {obj.title}",
        action_url="/education",
    )
    return obj


def update_event(acting_user: User, obj: EducationEvent, **data) -> EducationEvent:
    for key, val in data.items():
        if key in _EVENT_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    sync_event_for(obj)
    return obj


def delete_event(acting_user: User, obj: EducationEvent) -> None:
    delete_event_for(obj)
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


# ---------------------------------------------------------------------------
# Academic profiles
# ---------------------------------------------------------------------------

_PROFILE_FIELDS = {
    "institution_id", "programme_name", "credits_required",
    "credits_per_course_default", "graduation_year", "notes",
}


def get_or_create_academic_profile(
    acting_user: User, person_id: int
) -> EducationAcademicProfile:
    """Return the existing profile for a person, or create a blank one."""
    obj, _ = EducationAcademicProfile.objects.get_or_create(
        person_id=person_id,
        defaults={
            "household": get_active_household(),
            "created_by": acting_user,
            "updated_by": acting_user,
        },
    )
    return obj


def update_academic_profile(
    acting_user: User, profile: EducationAcademicProfile, **data
) -> EducationAcademicProfile:
    for key, val in data.items():
        if key in _PROFILE_FIELDS:
            setattr(profile, key, val)
    profile.updated_by = acting_user
    profile.save()
    return profile
