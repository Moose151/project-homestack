"""Subscribed and imported iCalendar feeds, normalised for the sync layer."""
from __future__ import annotations

from apps.scheduling.sources.fetching import fetch_calendar
from apps.scheduling.sources.ics import parse_calendar, resolve_times


def normalise_events(text: str, household_zone, *, max_events: int | None = None) -> list[dict]:
    """Parse an iCalendar document into the sync layer's normalised shape."""
    kwargs = {"max_events": max_events} if max_events else {}
    events = []
    for parsed in parse_calendar(text, **kwargs):
        start, end, all_day = resolve_times(parsed, household_zone)
        events.append({
            "uid": parsed.uid,
            "summary": parsed.summary or "(untitled)",
            "description": parsed.description,
            "location": parsed.location,
            "start_at": start,
            "end_at": end,
            "all_day": all_day,
            "is_range": False,
            "cancelled": parsed.cancelled,
            "sequence": parsed.sequence,
            "recurrence_rule": parsed.recurrence_rule,
        })
    return events


def build_events(source, *, household, years: tuple[int, ...] = ()) -> list[dict]:
    """Fetch and parse a subscribed feed.

    A one-time import has no URL to refresh from: its events were stored when it was created,
    so a later sync is a no-op rather than an error.
    """
    from apps.solace.bill_schedule import household_timezone

    if source.kind == "import" or not source.url:
        return []
    text = fetch_calendar(source.url)
    return normalise_events(text, household_timezone(household))
