"""Lead-time wording for scheduled notifications — docs/32 §8.

A bill, task or deadline is *due*: it can be "Due today" and it can be "Overdue". An
appointment or event is not — it simply happens, so it is "Today", "Tomorrow" or "Starts at
3:30 PM". A reminder reads as a reminder. Labelling a dentist appointment "Due today" (or
worse, "Overdue") is the bug this module exists to prevent.

The wording is derived from the calendar entry itself rather than hardcoded at each call
site, so in-app notifications, the notification bell and the Web Push payload — which all
render the same Notification.title — can never drift apart.
"""
from __future__ import annotations

# What a calendar entry *is*, for wording purposes.
TASK = "task"
EVENT = "event"
REMINDER = "reminder"


def entry_kind(event) -> str:
    """Classify a CalendarEvent for wording.

    Atlas reminders are recognised by their source record rather than ``event_kind``: the
    reminder sync payload deliberately leaves ``event_kind`` at the calendar default, so the
    source link is the only reliable signal.
    """
    if (getattr(event, "source_record_type", "") or "") == "AtlasReminder":
        return REMINDER
    if getattr(event, "event_kind", "") == "task":
        return TASK
    return EVENT


def _start_time_text(event, tz) -> str:
    local = event.start_at.astimezone(tz)
    hour = local.hour % 12 or 12
    meridiem = "AM" if local.hour < 12 else "PM"
    return f"{hour}:{local.minute:02d} {meridiem}"


def tomorrow_title(event) -> str:
    """Wording for the 24-hours-ahead lead."""
    kind = entry_kind(event)
    if kind == TASK:
        return "Due tomorrow"
    if kind == REMINDER:
        return "Reminder tomorrow"
    return "Tomorrow"


def today_title(event, tz) -> str:
    """Wording for the morning-of lead.

    A timed appointment gains the most from the actual start time, so it gets "Starts at
    3:30 PM" rather than a bare "Today". All-day entries have no meaningful time to show.
    """
    kind = entry_kind(event)
    if kind == TASK:
        return "Due today"
    if kind == REMINDER:
        return "Reminder today"
    if event.is_all_day or event.start_at is None:
        return "Today"
    return f"Starts at {_start_time_text(event, tz)}"


def due_now_title(event) -> str:
    """Wording for delivery at the entry's own scheduled time."""
    kind = entry_kind(event)
    if kind == TASK:
        return "Due now"
    if kind == REMINDER:
        return "Reminder"
    return "Starting now"
