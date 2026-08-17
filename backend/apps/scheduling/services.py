"""scheduling services — write operations for standalone calendar events.

Synced events (backed by node records) are managed via helpers.sync_event_for /
helpers.delete_event_for — never through these functions.
"""
from __future__ import annotations

from apps.accounts.models import User
from apps.core.assignment import apply_assignees, pop_assignees
from apps.core.models import get_active_household
from apps.scheduling import events
from apps.scheduling.models import CalendarEvent, RotatingSchedule, RotatingScheduleException


def create_event(acting_user: User, **data) -> CalendarEvent:
    people = pop_assignees(data)
    hidden_users = data.pop("hidden_from_users", [])
    household = get_active_household()
    event = CalendarEvent(
        household=household,
        created_by=acting_user,
        updated_by=acting_user,
        **data,
    )
    event.save()
    apply_assignees(event, people)
    event.hidden_from_users.set(hidden_users)
    events.event_created(event.id, household.id)
    return event


def update_event(acting_user: User, event: CalendarEvent, **data) -> CalendarEvent:
    people = pop_assignees(data)
    hidden_users = data.pop("hidden_from_users", None)
    if event.is_synced:
        raise ValueError("Synced events cannot be updated via the API.")
    allowed = {
        "title", "description", "start_at", "end_at", "is_all_day",
        "timezone", "recurrence_rule",
        "event_kind", "colour", "location", "provider", "contact", "visibility", "sensitivity",
    }
    for key, val in data.items():
        if key in allowed:
            setattr(event, key, val)
    event.updated_by = acting_user
    event.save()
    apply_assignees(event, people)
    if hidden_users is not None:
        event.hidden_from_users.set(hidden_users)
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


# ---------------------------------------------------------------------------
# Calendar sources
# ---------------------------------------------------------------------------

def create_calendar_source(acting_user, **data):
    """Create a source after validating its type and settings against the registry.

    A one-time import is read here, at creation, from posted text — it never holds a URL to be
    fetched again later. A subscription stores a destination-validated URL and is populated by
    the first sync; the preview endpoint is what lets the household check the feed before
    committing to it, so creation never performs an external fetch of its own.
    """
    from apps.core.models import get_active_household
    from apps.scheduling.models import CalendarSource
    from apps.scheduling.sources import registry
    from apps.scheduling.sources.fetching import validate_destination

    kind = data.get("kind", "")
    provider = data.get("provider", "")
    entry = registry.spec(kind, provider)
    settings_json = registry.validate_settings(kind, provider, data.get("settings_json", {}))

    url = (data.get("url") or "").strip()
    if entry["needs_url"]:
        # Refuse an internal destination at the point it is entered, not at the next sync.
        url = validate_destination(url)
    else:
        url = ""

    source = CalendarSource(
        household=get_active_household(),
        created_by=acting_user,
        updated_by=acting_user,
        name=(data.get("name") or entry["label"])[:120],
        kind=kind,
        provider=provider,
        is_enabled=data.get("is_enabled", True),
        colour=data.get("colour") or entry["colour"],
        category=data.get("category") or entry["category"],
        url=url,
        settings_json=settings_json,
        show_on_calendar=data.get("show_on_calendar", True),
        show_in_upcoming=data.get("show_in_upcoming", entry["default_show_in_upcoming"]),
        # Subscribed calendars stay quiet unless the household deliberately turns them on.
        notifications_enabled=data.get("notifications_enabled", False),
    )
    source.save()

    if kind == "import":
        _apply_import(source, data.get("ics_text") or "")
    return source


def _apply_import(source, ics_text: str):
    """Read a posted .ics once into a source that will never refresh itself."""
    from django.utils import timezone

    from apps.core.models import get_active_household
    from apps.scheduling.models import CalendarSource
    from apps.scheduling.sources.feeds import normalise_events
    from apps.scheduling.sources.sync import apply_events
    from apps.solace.bill_schedule import household_timezone

    household = get_active_household()
    zone = household_timezone(household)
    entries = normalise_events(ics_text, zone)
    apply_events(source, entries, household_zone=zone)
    CalendarSource.all_objects.filter(pk=source.pk).update(
        last_sync_at=timezone.now(),
        last_success_at=timezone.now(),
        sync_status=CalendarSource.Status.OK,
        sync_error="",
    )
    source.refresh_from_db()
    return source


def update_calendar_source(acting_user, source, **data):
    """Update presentation/behaviour. Kind and provider are fixed once created."""
    from apps.scheduling.sources import registry
    from apps.scheduling.sources.fetching import validate_destination

    entry = registry.spec(source.kind, source.provider)
    for field in (
        "name", "is_enabled", "colour", "category",
        "show_on_calendar", "show_in_upcoming", "notifications_enabled",
    ):
        if field in data:
            setattr(source, field, data[field])
    if "settings_json" in data:
        source.settings_json = registry.validate_settings(
            source.kind, source.provider, data["settings_json"],
        )
    if "url" in data and entry["needs_url"]:
        source.url = validate_destination(data["url"])
    source.updated_by = acting_user
    source.save()
    # Colour is mirrored onto the source's events so the calendar recolours immediately rather
    # than at the next sync.
    if "colour" in data:
        source.events.update(colour=source.colour)
    return source


def delete_calendar_source(acting_user, source) -> None:
    """Remove a source and the entries it owned — and nothing else.

    The events are the source's mirror, not household records, so they go with it. Anything
    hand-made, or owned by another source, is untouched: the FK cascade is scoped to this row.
    """
    source.events.all().delete()
    source.delete()
