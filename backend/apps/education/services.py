"""education services — write operations (Coding Standards §6).

Assessments (due dates) and class sessions (weekly timetable) mirror to the shared
calendar via the scheduling helper only (D7) — never CalendarEvent.objects directly.
"""
from __future__ import annotations

from datetime import date, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dateutil.relativedelta import relativedelta

from apps.accounts.models import User
from apps.core.assignment import apply_assignees, pop_assignees
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


def _notify_assigned(acting_user: User, person_ids, *, title: str, message: str, action_url: str = "") -> None:
    """Notify everyone an item is assigned to, skipping the acting user (D12)."""
    linked = getattr(acting_user, "person_profile", None)
    for person_id in person_ids or []:
        if linked is not None and linked.id == person_id:
            continue  # don't notify yourself about your own item
        notifications.notify_person_id(
            person_id, title=title, message=message, source_node="education",
            action_url=action_url, category="assigned_tasks",
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
    "title", "assessment_type", "course_id", "due_at", "is_all_day",
    "status", "priority", "weight", "description", "visibility", "sensitivity",
}


def create_assessment(acting_user: User, **data) -> EducationAssessment:
    people = pop_assignees(data)
    obj = EducationAssessment(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    apply_assignees(obj, people)
    sync_event_for(obj)
    events.assessment_created(obj.id, obj.household_id)
    _notify_assigned(
        acting_user, list(obj.assigned_to_people.values_list("id", flat=True)),
        title="New assignment",
        message=f"{obj.get_assessment_type_display()}: {obj.title}",
        action_url="/education",
    )
    return obj


def update_assessment(acting_user: User, obj: EducationAssessment, **data) -> EducationAssessment:
    people = pop_assignees(data)
    was_complete = obj.is_complete
    for key, val in data.items():
        if key in _ASSESSMENT_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    apply_assignees(obj, people)
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


# How often a timetabled class repeats. Values are the API contract; the frontend offers the
# labels. Deliberately a short, closed list of what a term timetable actually does, not a
# general recurrence builder.
CLASS_REPEAT_INTERVALS: dict[str, relativedelta] = {
    "weekly": relativedelta(weeks=1),
    "fortnightly": relativedelta(weeks=2),
    "every_3_weeks": relativedelta(weeks=3),
    "every_4_weeks": relativedelta(weeks=4),
    "monthly": relativedelta(months=1),
}

# A guard against a typo in the last-class date (2027 instead of 2026) quietly creating hundreds
# of classes and calendar events. A weekly class across a full year is ~52, so this is generous.
MAX_CLASS_SERIES_SESSIONS = 120


class ClassSeriesError(ValueError):
    """A repeat request that cannot produce a sensible series."""


def _household_zone(household) -> ZoneInfo:
    name = getattr(household, "timezone", "") or "UTC"
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def class_series_start_times(
    first_start, *, repeat: str, repeat_until: date, household=None
) -> list:
    """Every start datetime for a class repeating from `first_start` until `repeat_until`.

    Stepping happens in the household's own timezone, then converts back to UTC. Adding a
    timedelta to a UTC instant instead would silently move a 9am class to 8am or 10am for the
    half of the term on the other side of a daylight-saving change.

    `repeat_until` is inclusive and compared as a household-local date, so "last class 12 June"
    includes the class on 12 June.
    """
    interval = CLASS_REPEAT_INTERVALS.get(repeat)
    if interval is None:
        raise ClassSeriesError("Unknown repeat interval.")
    zone = _household_zone(household)
    local_first = first_start.astimezone(zone)
    if repeat_until < local_first.date():
        raise ClassSeriesError("The last class cannot be before the first one.")

    starts = []
    local = local_first
    while local.date() <= repeat_until:
        starts.append(local.astimezone(timezone.utc))
        if len(starts) > MAX_CLASS_SERIES_SESSIONS:
            raise ClassSeriesError(
                f"That range would create more than {MAX_CLASS_SERIES_SESSIONS} classes. "
                "Shorten it or choose a less frequent repeat."
            )
        # Re-attach the zone after arithmetic so the wall-clock time is preserved across a DST
        # boundary rather than drifting by an hour.
        naive_next = (local.replace(tzinfo=None) + interval)
        local = naive_next.replace(tzinfo=zone)
    return starts


def create_class_series(
    acting_user: User, *, repeat: str = "", repeat_until: date | None = None, **data
) -> list[EducationClassSession]:
    """Create a one-off class, or every occurrence of a repeating one.

    Returns the created sessions in date order. Without `repeat`/`repeat_until` this is exactly
    one session and behaves identically to `create_class_session`.
    """
    if not repeat or repeat_until is None:
        return [create_class_session(acting_user, **data)]

    first_start = data["start_at"]
    duration = (data.get("end_at") - first_start) if data.get("end_at") else None
    if duration is not None and duration.total_seconds() < 0:
        raise ClassSeriesError("A class cannot end before it starts.")

    household = get_active_household()
    starts = class_series_start_times(
        first_start, repeat=repeat, repeat_until=repeat_until, household=household
    )
    series_key = uuid4()
    created = []
    for start_at in starts:
        occurrence = dict(data)
        occurrence["start_at"] = start_at
        occurrence["end_at"] = (start_at + duration) if duration is not None else None
        occurrence["series_key"] = series_key
        created.append(create_class_session(acting_user, **occurrence))
    return created


def delete_class_series(acting_user: User, obj: EducationClassSession) -> int:
    """Delete every remaining class in the same series, including `obj`. Returns the count."""
    if obj.series_key is None:
        delete_class_session(acting_user, obj)
        return 1
    siblings = list(EducationClassSession.objects.filter(series_key=obj.series_key))
    for session in siblings:
        delete_class_session(acting_user, session)
    return len(siblings)


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
    "title", "event_type", "course_id", "institution_id",
    "start_at", "end_at", "is_all_day", "location", "description", "recurrence_rule", "visibility",
}


def create_event(acting_user: User, **data) -> EducationEvent:
    people = pop_assignees(data)
    obj = EducationEvent(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    apply_assignees(obj, people)
    sync_event_for(obj)
    events.school_event_created(obj.id, obj.household_id)
    _notify_assigned(
        acting_user, list(obj.assigned_to_people.values_list("id", flat=True)),
        title="New education event",
        message=f"{obj.get_event_type_display()}: {obj.title}",
        action_url="/education",
    )
    return obj


def update_event(acting_user: User, obj: EducationEvent, **data) -> EducationEvent:
    people = pop_assignees(data)
    for key, val in data.items():
        if key in _EVENT_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    apply_assignees(obj, people)
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
