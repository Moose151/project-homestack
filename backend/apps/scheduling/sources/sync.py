"""Mirroring a calendar source's events into CalendarEvent, repeatably.

The whole design rests on one identity rule: an event is identified by
``(calendar_source, external_uid)``. A feed that moves a fixture's kick-off, renames it or
changes its venue keeps the same UID, so the existing row is updated rather than a second one
appearing. Running the same sync twice therefore changes nothing the second time.

Disappearance is handled conservatively. Each sync bumps the source's ``sync_revision`` and
stamps every event it saw with it; an event whose revision falls behind is one the feed stopped
mentioning. Those are deleted only when they are still in the future — a fixture that was
cancelled or rescheduled should vanish, but a feed that only publishes the current season must
not silently erase the household's record of what already happened. Past entries are left
alone.
"""
from __future__ import annotations

from datetime import datetime, time as time_cls

from django.db import transaction
from django.utils import timezone

from apps.scheduling.models import CalendarEvent, CalendarSource

# Belt and braces alongside the parser's own cap: a provider bug must not be able to write an
# unbounded number of rows.
MAX_EVENTS_PER_SOURCE = 2000


def _redact(message: str, url: str) -> str:
    """Remove a source's own URL from a message before it is stored or returned."""
    if not url:
        return message
    cleaned = message.replace(url, "[calendar URL]")
    from urllib.parse import urlsplit
    parts = urlsplit(url)
    # Also drop a bare path/query echo, which is where subscription tokens live.
    if parts.path and len(parts.path) > 1:
        cleaned = cleaned.replace(parts.path, "[path]")
    if parts.query:
        cleaned = cleaned.replace(parts.query, "[query]")
    return cleaned


class SourceSyncError(Exception):
    """A sync that failed. The message is safe to show the household."""


def _as_datetime(value, household_zone, *, end_of_day: bool = False):
    """Normalise a provider's date/datetime into the aware datetime the calendar stores."""
    if isinstance(value, datetime):
        return value if timezone.is_aware(value) else value.replace(tzinfo=household_zone)
    if value is None:
        return None
    moment = time_cls.max if end_of_day else time_cls.min
    return datetime.combine(value, moment, tzinfo=household_zone)


def _payload(entry: dict, household_zone) -> dict:
    """One provider entry -> CalendarEvent field values.

    Providers may express timing either as dates (holidays, terms) or as resolved datetimes
    (parsed feeds); both are accepted so a provider does not have to know the storage shape.
    """
    # Both paths go through _as_datetime: a provider may hand back an already-aware datetime
    # (parsed feeds do), a naive one (a part-day holiday declared in local time), or a plain
    # date. Only routing the date path through normalisation let naive datetimes reach the ORM.
    start = _as_datetime(entry.get("start_at") or entry.get("start_date"), household_zone)
    end = entry.get("end_at")
    if end is None and entry.get("end_date") is not None:
        end = _as_datetime(entry["end_date"], household_zone, end_of_day=True)
    else:
        end = _as_datetime(end, household_zone)
    return {
        "title": (entry.get("summary") or "(untitled)")[:255],
        "description": entry.get("description", "")[:5000],
        "location": (entry.get("location") or "")[:255],
        "start_at": start,
        "end_at": end,
        "is_all_day": bool(entry.get("all_day")),
        "is_range": bool(entry.get("is_range")),
        "recurrence_rule": (entry.get("recurrence_rule") or "")[:512],
        "external_sequence": entry.get("sequence"),
    }


@transaction.atomic
def apply_events(source: CalendarSource, entries: list[dict], *, household_zone) -> dict:
    """Write one sync's worth of entries, returning a summary.

    Runs in a transaction so an overlapping job cannot interleave a partial revision, and takes
    a row lock on the source so two concurrent syncs of the same source serialise instead of
    both creating the same events.
    """
    locked = CalendarSource.all_objects.select_for_update().get(pk=source.pk)
    revision = locked.sync_revision + 1

    if len(entries) > MAX_EVENTS_PER_SOURCE:
        raise SourceSyncError(
            f"That calendar has more than {MAX_EVENTS_PER_SOURCE} events, which is too many.",
        )

    existing = {
        event.external_uid: event
        for event in CalendarEvent.all_objects.filter(calendar_source=locked)
    }
    created = updated = cancelled = 0
    seen: set[str] = set()

    for entry in entries:
        uid = (entry.get("uid") or "").strip()[:255]
        if not uid or uid in seen:
            # No UID means no stable identity, so mirroring it would duplicate next time.
            continue
        seen.add(uid)
        fields = _payload(entry, household_zone)
        if fields["start_at"] is None:
            continue

        event = existing.get(uid)
        if entry.get("cancelled"):
            # A cancelled entry is removed rather than shown as a ghost fixture.
            if event is not None:
                event.delete()
                cancelled += 1
            continue

        if event is None:
            CalendarEvent.objects.create(
                household=locked.household,
                calendar_source=locked,
                external_uid=uid,
                last_seen_revision=revision,
                colour=locked.colour,
                created_by=locked.created_by,
                updated_by=locked.updated_by,
                **fields,
            )
            created += 1
        else:
            for name, value in fields.items():
                setattr(event, name, value)
            event.last_seen_revision = revision
            event.colour = locked.colour
            event.deleted_at = None
            event.save()
            updated += 1

    # Entries the feed stopped mentioning: drop future ones, keep history.
    removed = 0
    stale = CalendarEvent.all_objects.filter(
        calendar_source=locked, start_at__gte=timezone.now(),
    ).exclude(last_seen_revision=revision)
    removed = stale.count()
    stale.delete()

    locked.sync_revision = revision
    locked.save(update_fields=["sync_revision"])
    return {"created": created, "updated": updated, "cancelled": cancelled, "removed": removed}


def sync_source(source: CalendarSource, *, household=None) -> dict:
    """Refresh one source, recording success or failure on the row itself.

    Failure is contained: the error is stored and returned, never raised past this point, so one
    unreachable feed cannot abort a scheduled run over every other source.
    """
    from apps.core.models import get_active_household
    from apps.scheduling.sources.registry import provider_for, spec
    from apps.solace.bill_schedule import household_timezone

    household = household or get_active_household()
    zone = household_timezone(household)
    now = timezone.now()

    if not spec(source.kind, source.provider)["syncs"]:
        # A one-time import has nothing to refresh from.
        return {"skipped": True}

    try:
        entries = provider_for(source)(source, household=household)
        result = apply_events(source, entries, household_zone=zone)
    except Exception as exc:  # noqa: BLE001 — deliberately contained, see docstring
        # The stored message is shown in the UI and kept indefinitely, and an unexpected
        # exception from a networking library may well quote the URL it was given — which for a
        # tokenised subscription is a bearer credential. Redact it before it is persisted.
        message = _redact(str(exc), source.url)[:500]
        CalendarSource.all_objects.filter(pk=source.pk).update(
            last_sync_at=now,
            sync_status=CalendarSource.Status.ERROR,
            sync_error=message,
        )
        return {"error": message}

    CalendarSource.all_objects.filter(pk=source.pk).update(
        last_sync_at=now,
        last_success_at=now,
        sync_status=CalendarSource.Status.OK,
        sync_error="",
    )
    return result


def sync_due_sources(*, now=None, interval_hours: int = 6) -> dict:
    """Refresh every enabled, syncable source that is due.

    A few hours is ample for a season fixture list or a school calendar; polling harder would
    be rude to the provider and buys nothing.
    """
    from datetime import timedelta

    now = now or timezone.now()
    due_before = now - timedelta(hours=interval_hours)
    synced = failed = 0
    for source in CalendarSource.objects.filter(is_enabled=True):
        if not spec_syncs(source):
            continue
        if source.last_success_at and source.last_success_at > due_before:
            continue
        outcome = sync_source(source)
        if outcome.get("error"):
            failed += 1
        elif not outcome.get("skipped"):
            synced += 1
    return {"synced": synced, "failed": failed}


def spec_syncs(source: CalendarSource) -> bool:
    from apps.scheduling.sources.registry import PROVIDERS
    entry = PROVIDERS.get((source.kind, source.provider))
    return bool(entry and entry["syncs"])
