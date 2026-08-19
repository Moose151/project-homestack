"""A deliberately small iCalendar (RFC 5545) reader.

Only the parts HomeStack mirrors are read: VEVENT identity, timing, the handful of display
fields, and the recurrence rule passed through for display. Everything else is skipped rather
than half-understood.

Written against the spec instead of pulling in a parsing dependency because the input is
hostile by definition — it is fetched from a URL a user supplied — and the whole surface is
worth being able to read in one sitting. The parser only ever produces data: text is unescaped
into plain strings and never interpreted as HTML or markup, and nothing here evaluates,
executes or resolves anything from the feed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MAX_EVENTS = 2000
# Long enough for any real feed line; a single absurd line is a sign of a hostile payload.
MAX_LINE_LENGTH = 8000

_DATE = re.compile(r"^(\d{4})(\d{2})(\d{2})$")
_DATETIME = re.compile(r"^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})(Z)?$")


class IcsParseError(Exception):
    """A feed that could not be understood. The message is safe to show the household."""


@dataclass
class IcsEvent:
    uid: str
    summary: str = ""
    description: str = ""
    location: str = ""
    status: str = ""
    start: datetime | date | None = None
    end: datetime | date | None = None
    all_day: bool = False
    sequence: int | None = None
    recurrence_rule: str = ""
    extra_recurrence: list[str] = field(default_factory=list)

    @property
    def cancelled(self) -> bool:
        return self.status.upper() == "CANCELLED"


def _unfold(text: str) -> list[str]:
    """Join RFC 5545 folded lines (a continuation begins with a space or tab)."""
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
        if len(lines[-1]) > MAX_LINE_LENGTH:
            raise IcsParseError("That calendar contains an unreasonably long line.")
    return lines


def _split_line(line: str) -> tuple[str, dict[str, str], str]:
    """`NAME;PARAM=VALUE:value` -> (NAME, params, value)."""
    head, _, value = line.partition(":")
    pieces = head.split(";")
    name = pieces[0].strip().upper()
    params: dict[str, str] = {}
    for piece in pieces[1:]:
        key, _, param_value = piece.partition("=")
        params[key.strip().upper()] = param_value.strip().strip('"')
    return name, params, value


def _unescape(value: str) -> str:
    """Undo RFC 5545 text escaping. The result is plain text, never markup."""
    out: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char == "\\" and index + 1 < len(value):
            nxt = value[index + 1]
            out.append({"n": "\n", "N": "\n", ",": ",", ";": ";", "\\": "\\"}.get(nxt, nxt))
            index += 2
            continue
        out.append(char)
        index += 1
    return "".join(out)


def _zone(name: str):
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def _parse_datetime(value: str, params: dict[str, str]):
    """Return an aware datetime, or a plain date for a VALUE=DATE (all-day) property."""
    value = value.strip()
    if params.get("VALUE", "").upper() == "DATE" or _DATE.match(value):
        match = _DATE.match(value)
        if not match:
            raise IcsParseError("That calendar has an unreadable date.")
        return date(int(match[1]), int(match[2]), int(match[3]))
    match = _DATETIME.match(value)
    if not match:
        raise IcsParseError("That calendar has an unreadable date.")
    naive = datetime(
        int(match[1]), int(match[2]), int(match[3]),
        int(match[4]), int(match[5]), int(match[6]),
    )
    if match[7]:  # trailing Z — already UTC
        return naive.replace(tzinfo=dt_timezone.utc)
    tzid = params.get("TZID")
    zone = _zone(tzid) if tzid else None
    # A floating time (no TZID, no Z) is defined as local to the reader; the caller supplies the
    # household zone, so it is attached later rather than guessed here.
    return naive.replace(tzinfo=zone) if zone else naive


def parse_calendar(text: str, *, max_events: int = MAX_EVENTS) -> list[IcsEvent]:
    """Parse VEVENTs out of an iCalendar document.

    Events without a UID or without a start are skipped rather than invented: both are required
    for stable re-sync, and a synthetic identity would duplicate on the next refresh.
    """
    if "BEGIN:VCALENDAR" not in text.upper():
        raise IcsParseError("That file is not a calendar.")

    events: list[IcsEvent] = []
    current: IcsEvent | None = None
    for line in _unfold(text):
        if not line.strip():
            continue
        name, params, value = _split_line(line)
        if name == "BEGIN" and value.strip().upper() == "VEVENT":
            current = IcsEvent(uid="")
            continue
        if name == "END" and value.strip().upper() == "VEVENT":
            if current and current.uid and current.start is not None:
                events.append(current)
                if len(events) > max_events:
                    raise IcsParseError(
                        f"That calendar has more than {max_events} events, which is too many to import.",
                    )
            current = None
            continue
        if current is None:
            continue

        try:
            if name == "UID":
                current.uid = value.strip()[:255]
            elif name == "SUMMARY":
                current.summary = _unescape(value)[:255]
            elif name == "DESCRIPTION":
                current.description = _unescape(value)[:5000]
            elif name == "LOCATION":
                current.location = _unescape(value)[:255]
            elif name == "STATUS":
                current.status = value.strip()[:40]
            elif name == "SEQUENCE":
                current.sequence = int(value.strip() or 0)
            elif name == "RRULE":
                current.recurrence_rule = f"RRULE:{value.strip()}"[:512]
            elif name in ("RDATE", "EXDATE"):
                current.extra_recurrence.append(f"{name}:{value.strip()}"[:512])
            elif name == "DTSTART":
                current.start = _parse_datetime(value, params)
                current.all_day = isinstance(current.start, date) and not isinstance(current.start, datetime)
            elif name == "DTEND":
                current.end = _parse_datetime(value, params)
            elif name == "DURATION":
                current.end = None  # resolved against DTSTART by the caller if needed
        except (ValueError, IcsParseError):
            # One malformed property should not discard an otherwise usable feed; the event is
            # dropped at END:VEVENT if what remains is not enough to identify it.
            continue

    if not events:
        raise IcsParseError("That calendar contains no events.")
    return events


def resolve_times(event: IcsEvent, household_zone) -> tuple[datetime, datetime | None, bool]:
    """Convert a parsed event into the aware start/end HomeStack stores.

    All-day entries keep their all-day nature: iCalendar's exclusive DTEND (the day *after* the
    last day) is converted to an inclusive end so a one-day holiday does not render as two.
    Floating times are anchored to the household's zone, which is what "local time" means here.
    """
    start = event.start
    end = event.end
    all_day = event.all_day

    if isinstance(start, datetime):
        if start.tzinfo is None:
            start = start.replace(tzinfo=household_zone)
    elif isinstance(start, date):
        start = datetime.combine(start, datetime.min.time(), tzinfo=household_zone)

    if isinstance(end, datetime):
        if end.tzinfo is None:
            end = end.replace(tzinfo=household_zone)
    elif isinstance(end, date):
        # Exclusive per RFC 5545 for DATE values.
        end = datetime.combine(end - timedelta(days=1), datetime.max.time(), tzinfo=household_zone)
    else:
        end = None

    return start, end, all_day
