"""scheduling services — write operations for standalone calendar events.

Synced events (backed by node records) are managed via helpers.sync_event_for /
helpers.delete_event_for — never through these functions.
"""
from __future__ import annotations

from apps.accounts.models import User
from apps.core.assignment import apply_assignees, pop_assignees
from apps.core.models import get_active_household
from apps.scheduling.models import CalendarEvent, RotatingSchedule, RotatingScheduleException


def create_event(acting_user: User, **data) -> CalendarEvent:
    people = pop_assignees(data)
    household = get_active_household()
    event = CalendarEvent(
        household=household,
        created_by=acting_user,
        updated_by=acting_user,
        **data,
    )
    event.save()
    apply_assignees(event, people)
    return event


def update_event(acting_user: User, event: CalendarEvent, **data) -> CalendarEvent:
    people = pop_assignees(data)
    if event.is_synced:
        raise ValueError("Synced events cannot be updated via the API.")
    allowed = {
        "title", "description", "start_at", "end_at", "is_all_day",
        "timezone", "recurrence_rule",
        "colour", "location", "visibility", "sensitivity",
    }
    for key, val in data.items():
        if key in allowed:
            setattr(event, key, val)
    event.updated_by = acting_user
    event.save()
    apply_assignees(event, people)
    return event


def delete_event(acting_user: User, event: CalendarEvent) -> None:
    if event.is_synced:
        raise ValueError("Synced events cannot be deleted via the API.")
    event.updated_by = acting_user
    event.save(update_fields=["updated_by", "updated_at"])
    event.soft_delete()


def create_rotating_schedule(acting_user: User, **data) -> RotatingSchedule:
    people = data.pop("people", [])
    schedule = RotatingSchedule(
        household=get_active_household(),
        created_by=acting_user,
        updated_by=acting_user,
        **data,
    )
    schedule.save()
    schedule.people.set(people)
    return schedule


def update_rotating_schedule(
    acting_user: User, schedule: RotatingSchedule, **data
) -> RotatingSchedule:
    people = data.pop("people", None)
    allowed = {
        "title", "primary_label", "secondary_label", "anchor_date", "cycle_pattern",
        "primary_colour", "secondary_colour", "visibility", "is_active",
    }
    for key, value in data.items():
        if key in allowed:
            setattr(schedule, key, value)
    schedule.updated_by = acting_user
    schedule.save()
    if people is not None:
        schedule.people.set(people)
    return schedule


def delete_rotating_schedule(acting_user: User, schedule: RotatingSchedule) -> None:
    schedule.updated_by = acting_user
    schedule.save(update_fields=["updated_by", "updated_at"])
    schedule.soft_delete()


def set_rotating_schedule_exception(
    acting_user: User,
    schedule: RotatingSchedule,
    date,
    *,
    state: str,
    note: str = "",
) -> RotatingScheduleException:
    exception = RotatingScheduleException.all_objects.filter(
        schedule=schedule, date=date
    ).first()
    if exception is None:
        exception = RotatingScheduleException(
            household=schedule.household,
            schedule=schedule,
            date=date,
            created_by=acting_user,
        )
    exception.state = state
    exception.note = note
    exception.deleted_at = None
    exception.updated_by = acting_user
    exception.save()
    return exception


def delete_rotating_schedule_exception(
    acting_user: User, schedule: RotatingSchedule, date
) -> None:
    exception = RotatingScheduleException.objects.filter(
        schedule=schedule, date=date
    ).first()
    if exception is None:
        return
    exception.updated_by = acting_user
    exception.save(update_fields=["updated_by", "updated_at"])
    exception.soft_delete()
