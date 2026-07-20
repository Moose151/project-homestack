"""education selectors — read-only queries (Coding Standards §6, D9)."""
from __future__ import annotations

from django.db import connection
from django.db.models import Q
from django.utils import timezone

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
from apps.permissions.visibility import apply_visibility


def _search(qs, query: str, fields: list[str]):
    """Filter ``qs`` by ``query`` across ``fields`` (D9). Postgres FTS in prod, icontains on SQLite."""
    if connection.vendor == "postgresql":
        from django.contrib.postgres.search import SearchQuery, SearchVector
        return qs.annotate(_search=SearchVector(*fields)).filter(_search=SearchQuery(query))
    clause = Q()
    for field in fields:
        clause |= Q(**{f"{field}__icontains": query})
    return qs.filter(clause)


# ---------------------------------------------------------------------------
# Institutions
# ---------------------------------------------------------------------------

def list_institutions(user=None) -> list[EducationInstitution]:
    qs = EducationInstitution.objects.order_by("name")
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_institution(pk: int) -> EducationInstitution | None:
    return EducationInstitution.objects.filter(pk=pk).first()


# ---------------------------------------------------------------------------
# Courses
# ---------------------------------------------------------------------------

def list_courses(user=None, *, include_archived: bool = False, student_id: int | None = None):
    qs = EducationCourse.objects.select_related("institution", "student").order_by("name")
    if not include_archived:
        qs = qs.filter(is_archived=False)
    if student_id is not None:
        qs = qs.filter(student_id=student_id)
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_course(pk: int) -> EducationCourse | None:
    return EducationCourse.objects.filter(pk=pk).first()


# ---------------------------------------------------------------------------
# Assessments
# ---------------------------------------------------------------------------

def list_assessments(
    user=None, *, upcoming_only: bool = False, open_only: bool = False,
    course_id: int | None = None, person_id: int | None = None, limit: int | None = None,
):
    qs = EducationAssessment.objects.select_related("course").order_by("due_at", "-updated_at")
    if upcoming_only:
        qs = qs.filter(due_at__gte=timezone.now())
    if open_only:
        qs = qs.exclude(status__in=[EducationAssessment.Status.SUBMITTED, EducationAssessment.Status.DONE])
    if course_id is not None:
        qs = qs.filter(course_id=course_id)
    if person_id is not None:
        qs = qs.filter(assigned_to_person_id=person_id)
    if user is not None:
        qs = apply_visibility(qs, user)
    if limit is not None:
        qs = qs[:limit]
    return list(qs)


def get_assessment(pk: int) -> EducationAssessment | None:
    return EducationAssessment.objects.filter(pk=pk).first()


# ---------------------------------------------------------------------------
# Assessment notes
# ---------------------------------------------------------------------------

def list_assessment_notes(assessment: EducationAssessment) -> list[EducationAssessmentNote]:
    return list(assessment.notes.order_by("created_at"))


def get_assessment_note(pk: int) -> EducationAssessmentNote | None:
    return EducationAssessmentNote.objects.filter(pk=pk).first()


# ---------------------------------------------------------------------------
# Assessment files
# ---------------------------------------------------------------------------

def list_assessment_files(assessment: EducationAssessment) -> list[EducationAssessmentFile]:
    return list(assessment.files.order_by("created_at"))


def get_assessment_file(pk: int) -> EducationAssessmentFile | None:
    return EducationAssessmentFile.objects.filter(pk=pk).first()


# ---------------------------------------------------------------------------
# Class sessions (timetable)
# ---------------------------------------------------------------------------

def list_class_sessions(user=None, *, course_id: int | None = None, student_id: int | None = None):
    qs = EducationClassSession.objects.select_related("course").order_by("start_at")
    if course_id is not None:
        qs = qs.filter(course_id=course_id)
    if student_id is not None:
        qs = qs.filter(student_id=student_id)
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_class_session(pk: int) -> EducationClassSession | None:
    return EducationClassSession.objects.filter(pk=pk).first()


# ---------------------------------------------------------------------------
# Education events
# ---------------------------------------------------------------------------

def list_events(
    user=None, *, upcoming_only: bool = False, course_id: int | None = None,
    person_id: int | None = None, limit: int | None = None,
):
    qs = EducationEvent.objects.select_related("course", "institution").order_by("start_at")
    if upcoming_only:
        qs = qs.filter(start_at__gte=timezone.now())
    if course_id is not None:
        qs = qs.filter(course_id=course_id)
    if person_id is not None:
        qs = qs.filter(assigned_to_person_id=person_id)
    if user is not None:
        qs = apply_visibility(qs, user)
    if limit is not None:
        qs = qs[:limit]
    return list(qs)


def get_event(pk: int) -> EducationEvent | None:
    return EducationEvent.objects.filter(pk=pk).first()


# ---------------------------------------------------------------------------
# Academic profiles
# ---------------------------------------------------------------------------

def get_academic_profile(person_id: int) -> EducationAcademicProfile | None:
    return EducationAcademicProfile.objects.select_related("institution", "person").filter(person_id=person_id).first()


def list_courses_for_profile(person_id: int, user=None):
    """All active (non-archived) courses for a person, with date-based status classification."""
    from django.utils import timezone
    today = timezone.now().date()
    qs = (
        EducationCourse.objects.select_related("institution")
        .filter(student_id=person_id, is_archived=False)
        .order_by("start_date", "name")
    )
    if user is not None:
        qs = apply_visibility(qs, user)
    courses = list(qs)
    current, upcoming, past = [], [], []
    for c in courses:
        if c.is_completed:
            past.append(c)
        elif c.start_date and c.end_date:
            if c.start_date <= today <= c.end_date:
                current.append(c)
            elif c.start_date > today:
                upcoming.append(c)
            else:
                past.append(c)
        elif c.start_date and c.start_date <= today:
            current.append(c)
        elif c.start_date and c.start_date > today:
            upcoming.append(c)
        else:
            current.append(c)  # no dates → assume active
    return {"current": current, "upcoming": upcoming, "past": past}


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search_education(user, query: str) -> dict:
    """Permission-filtered FTS across courses, assessments and class sessions (D9)."""
    courses_qs = _search(EducationCourse.objects.all(), query, ["name", "code", "teacher", "description"])
    assessments_qs = _search(EducationAssessment.objects.all(), query, ["title", "description"])
    sessions_qs = _search(EducationClassSession.objects.all(), query, ["title", "location"])
    events_qs = _search(EducationEvent.objects.all(), query, ["title", "location", "description"])

    if user is not None:
        courses_qs = apply_visibility(courses_qs, user)
        assessments_qs = apply_visibility(assessments_qs, user)
        sessions_qs = apply_visibility(sessions_qs, user)
        events_qs = apply_visibility(events_qs, user)

    return {
        "courses": list(courses_qs.order_by("name")),
        "assessments": list(assessments_qs.order_by("due_at", "-updated_at")),
        "class_sessions": list(sessions_qs.order_by("start_at")),
        "events": list(events_qs.order_by("start_at")),
    }
