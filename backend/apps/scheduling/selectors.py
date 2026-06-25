"""scheduling selectors — read-only queries (Coding Standards §6)."""
from __future__ import annotations

from apps.permissions.visibility import apply_visibility
from apps.scheduling.models import CalendarEvent


def list_events(
    user=None,
    *,
    start=None,
    end=None,
    node: str | None = None,
    person: int | None = None,
    upcoming_only: bool = False,
) -> list[CalendarEvent]:
    """Events the user may see, optionally windowed and filtered (D10).

    start/end: datetime window over ``start_at`` ([start, end)). node: source node key.
    person: ``assigned_to_person_id``. Permission filter is applied last.
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
        qs = qs.filter(assigned_to_person_id=person)
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_event(pk: int) -> CalendarEvent | None:
    return CalendarEvent.objects.filter(pk=pk).first()
