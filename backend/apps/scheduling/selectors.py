"""scheduling selectors — read-only queries (Coding Standards §6)."""
from __future__ import annotations

from django.db import connection
from django.db.models import Q

from apps.permissions.visibility import apply_visibility
from apps.scheduling.models import CalendarEvent, RotatingSchedule, RotatingScheduleException


def list_events(
    user=None,
    *,
    start=None,
    end=None,
    node: str | None = None,
    person: int | None = None,
    upcoming_only: bool = False,
    sensitive_unlocked: bool = False,
) -> list[CalendarEvent]:
    """Events the user may see, optionally windowed and filtered (D10).

    start/end: datetime window over ``start_at`` ([start, end)). node: source node key.
    person: matches an event assigned to that person among any of its assignees.
    Permission filter is applied last.
    """
    qs = CalendarEvent.objects.order_by("start_at")
    if upcoming_only:
        from django.utils import timezone
        qs = qs.filter(start_at__gte=timezone.now())
    if start is not None:
        qs = qs.filter(start_at__gte=start)
    if end is not None:
        qs = qs.filter(start_at__lt=end)
    if node:
        qs = qs.filter(source_node__key=node)
    if person:
        qs = qs.filter(assigned_to_people__id=person).distinct()
    if user is not None:
        qs = apply_visibility(qs, user)
    if not sensitive_unlocked:
        qs = qs.exclude(sensitivity__in=["financial", "health", "document", "private"])
        qs = qs.exclude(visibility="sensitive")
    return list(qs)


def get_event(pk: int) -> CalendarEvent | None:
    return CalendarEvent.objects.filter(pk=pk).first()


def search_events(user, query: str, *, sensitive_unlocked: bool = False) -> list[CalendarEvent]:
    """Permission-filtered search over live Calendar rows for global search (D9)."""
    qs = CalendarEvent.objects.select_related("source_node")
    if connection.vendor == "postgresql":
        from django.contrib.postgres.search import SearchQuery, SearchVector
        qs = qs.annotate(
            _search=SearchVector("title", "description", "location")
        ).filter(_search=SearchQuery(query))
    else:
        qs = qs.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(location__icontains=query)
        )
    if user is not None:
        qs = apply_visibility(qs, user)
    if not sensitive_unlocked:
        qs = qs.exclude(sensitivity__in=["financial", "health", "document", "private"])
        qs = qs.exclude(visibility="sensitive")
    return list(qs.order_by("start_at")[:20])


def list_rotating_schedules(user=None, *, active_only: bool = False) -> list[RotatingSchedule]:
    qs = RotatingSchedule.objects.prefetch_related("people").order_by("title")
    if active_only:
        qs = qs.filter(is_active=True)
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_rotating_schedule(pk: int, user=None) -> RotatingSchedule | None:
    qs = RotatingSchedule.objects.prefetch_related("people").filter(pk=pk)
    if user is not None:
        qs = apply_visibility(qs, user)
    return qs.first()


def expand_rotating_schedules(user, *, start, end) -> list[dict]:
    """Expand visible active schedules for [start, end) without materialising events."""
    from datetime import timedelta

    schedules = list_rotating_schedules(user, active_only=True)
    if not schedules:
        return []
    schedule_ids = [schedule.id for schedule in schedules]
    exceptions = {
        (exception.schedule_id, exception.date): exception
        for exception in RotatingScheduleException.objects.filter(
            schedule_id__in=schedule_ids,
            date__gte=start,
            date__lt=end,
        )
    }
    people_by_schedule = {
        schedule.id: [person.id for person in schedule.people.all()]
        for schedule in schedules
    }
    rows: list[dict] = []
    day = start
    while day < end:
        for schedule in schedules:
            planned_state = schedule.state_for_date(day)
            exception = exceptions.get((schedule.id, day))
            state = exception.state if exception else planned_state
            primary = state == "primary"
            rows.append({
                "id": f"rotation-{schedule.id}-{day.isoformat()}",
                "schedule_id": schedule.id,
                "schedule_title": schedule.title,
                "date": day.isoformat(),
                "state": state,
                "planned_state": planned_state,
                "label": schedule.primary_label if primary else schedule.secondary_label,
                "colour": schedule.primary_colour if primary else schedule.secondary_colour,
                "is_override": exception is not None,
                "note": exception.note if exception else "",
                "person_ids": people_by_schedule[schedule.id],
            })
        day += timedelta(days=1)
    return rows
