"""scheduling services — write operations for standalone calendar events.

Synced events (backed by node records) are managed via helpers.sync_event_for /
helpers.delete_event_for — never through these functions.
"""
from __future__ import annotations

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.scheduling.models import CalendarEvent


def create_event(acting_user: User, **data) -> CalendarEvent:
    household = get_active_household()
    event = CalendarEvent(
        household=household,
        created_by=acting_user,
        updated_by=acting_user,
        **data,
    )
    event.save()
    return event


def update_event(acting_user: User, event: CalendarEvent, **data) -> CalendarEvent:
    if event.is_synced:
        raise ValueError("Synced events cannot be updated via the API.")
    allowed = {
        "title", "description", "start_at", "end_at", "is_all_day",
        "timezone", "recurrence_rule", "assigned_to_person_id",
        "colour", "location", "visibility", "sensitivity",
    }
    for key, val in data.items():
        if key in allowed:
            setattr(event, key, val)
    event.updated_by = acting_user
    event.save()
    return event


def delete_event(acting_user: User, event: CalendarEvent) -> None:
    if event.is_synced:
        raise ValueError("Synced events cannot be deleted via the API.")
    event.updated_by = acting_user
    event.save(update_fields=["updated_by", "updated_at"])
    event.soft_delete()
