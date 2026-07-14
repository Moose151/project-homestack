"""education selectors — read-only queries (Coding Standards §6, D9)."""
from __future__ import annotations

from django.db import connection
from django.db.models import Q
from django.utils import timezone

from apps.education.models import (
    EducationAssessment,
    EducationClassSession,
    EducationCourse,
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
# Search
# ---------------------------------------------------------------------------

def search_education(user, query: str) -> dict:
    """Permission-filtered FTS across courses, assessments and class sessions (D9)."""
    courses_qs = _search(EducationCourse.objects.all(), query, ["name", "code", "teacher", "description"])
    assessments_qs = _search(EducationAssessment.objects.all(), query, ["title", "description"])
    sessions_qs = _search(EducationClassSession.objects.all(), query, ["title", "location"])

    if user is not None:
        courses_qs = apply_visibility(courses_qs, user)
        assessments_qs = apply_visibility(assessments_qs, user)
        sessions_qs = apply_visibility(sessions_qs, user)

    return {
        "courses": list(courses_qs.order_by("name")),
        "assessments": list(assessments_qs.order_by("due_at", "-updated_at")),
        "class_sessions": list(sessions_qs.order_by("start_at")),
    }
