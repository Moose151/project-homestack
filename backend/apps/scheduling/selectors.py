"""scheduling selectors — read-only queries (Coding Standards §6)."""
from __future__ import annotations

from django.db.models import Q

from apps.permissions.visibility import apply_visibility
from apps.scheduling.models import CalendarEvent


def list_events(user=None, *, upcoming_only: bool = False) -> list[CalendarEvent]:
    qs = CalendarEvent.objects.order_by("start_at")
    if upcoming_only:
        from django.utils import timezone
        qs = qs.filter(start_at__gte=timezone.now())
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_event(pk: int) -> CalendarEvent | None:
    return CalendarEvent.objects.filter(pk=pk).first()
