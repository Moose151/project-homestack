"""Australian school terms and holidays.

Term dates are published per system per year by each state education department, so — like
public holidays — they are shipped as dated data with provenance rather than derived. The
provider structure deliberately keys on a *system* rather than a state alone: Catholic and
independent schools frequently differ from the state system by a day or more at each boundary,
so pretending one set of dates covers every school in a state would quietly be wrong.

Only systems with reliable published term dates are offered. Anything else should use a
subscribed ICS feed from the school itself, which is what the subscription provider is for.

Ranges, not days: a term is one entry spanning the term, and a break is one entry spanning the
break. Generating an event per day would bury the rest of the calendar for eleven weeks.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

DATA_SOURCE_NOTE = "State education department published term dates"

# system slug -> (label, state)
SCHOOL_SYSTEMS = {
    "qld_state": ("Queensland State Schools", "QLD"),
    "nsw_state": ("NSW Public Schools", "NSW"),
    "vic_state": ("Victorian Government Schools", "VIC"),
}


@dataclass(frozen=True)
class Term:
    number: int
    start: date
    end: date


# system -> year -> terms. Sourced from each department's published term-date pages.
TERMS: dict[str, dict[int, list[Term]]] = {
    "qld_state": {
        2025: [
            Term(1, date(2025, 1, 28), date(2025, 4, 4)),
            Term(2, date(2025, 4, 22), date(2025, 6, 27)),
            Term(3, date(2025, 7, 14), date(2025, 9, 19)),
            Term(4, date(2025, 10, 7), date(2025, 12, 12)),
        ],
        2026: [
            Term(1, date(2026, 1, 27), date(2026, 4, 2)),
            Term(2, date(2026, 4, 20), date(2026, 6, 26)),
            Term(3, date(2026, 7, 13), date(2026, 9, 18)),
            Term(4, date(2026, 10, 6), date(2026, 12, 11)),
        ],
    },
    "nsw_state": {
        2025: [
            Term(1, date(2025, 2, 6), date(2025, 4, 11)),
            Term(2, date(2025, 4, 30), date(2025, 7, 4)),
            Term(3, date(2025, 7, 22), date(2025, 9, 26)),
            Term(4, date(2025, 10, 13), date(2025, 12, 19)),
        ],
        2026: [
            Term(1, date(2026, 1, 28), date(2026, 4, 2)),
            Term(2, date(2026, 4, 20), date(2026, 7, 3)),
            Term(3, date(2026, 7, 21), date(2026, 9, 25)),
            Term(4, date(2026, 10, 12), date(2026, 12, 18)),
        ],
    },
    "vic_state": {
        2025: [
            Term(1, date(2025, 1, 29), date(2025, 4, 4)),
            Term(2, date(2025, 4, 22), date(2025, 7, 4)),
            Term(3, date(2025, 7, 21), date(2025, 9, 19)),
            Term(4, date(2025, 10, 6), date(2025, 12, 19)),
        ],
        2026: [
            Term(1, date(2026, 1, 28), date(2026, 4, 2)),
            Term(2, date(2026, 4, 20), date(2026, 7, 3)),
            Term(3, date(2026, 7, 20), date(2026, 9, 18)),
            Term(4, date(2026, 10, 5), date(2026, 12, 18)),
        ],
    },
}


def system_label(system: str) -> str:
    return SCHOOL_SYSTEMS.get(system, (system, ""))[0]


def terms_for(system: str, year: int) -> list[Term]:
    return TERMS.get(system, {}).get(year, [])


def build_events(source, *, household, years: tuple[int, ...] = ()) -> list[dict]:
    """Term and break ranges for the configured school system.

    Breaks are derived from the gap between consecutive terms, which is exactly what a school
    holiday is — deriving it avoids a second data table that could disagree with the first.
    """
    from django.utils import timezone

    settings = source.settings_json or {}
    system = settings.get("system", "")
    show_terms = settings.get("show_terms", True)
    show_holidays = settings.get("show_holidays", True)

    this_year = timezone.localdate().year
    span = years or (this_year, this_year + 1)
    label = system_label(system)

    events: list[dict] = []
    for year in span:
        terms = terms_for(system, year)
        if not terms:
            continue
        for term in terms:
            if show_terms:
                events.append({
                    "uid": f"auschool-{system}-{year}-term{term.number}",
                    "summary": f"Term {term.number}",
                    "description": f"{label} · {DATA_SOURCE_NOTE}",
                    "location": "",
                    "start_date": term.start,
                    "end_date": term.end,
                    "all_day": True,
                    "is_range": True,
                    "cancelled": False,
                })
        if show_holidays:
            # The break after each term, and the summer break into the following year's Term 1.
            following = terms_for(system, year + 1)
            boundaries = list(zip(terms, terms[1:])) + (
                [(terms[-1], following[0])] if following else []
            )
            for earlier, later in boundaries:
                start = _next_day(earlier.end)
                end = _previous_day(later.start)
                if start > end:
                    continue
                events.append({
                    "uid": f"auschool-{system}-{start.isoformat()}-break",
                    "summary": "School holidays",
                    "description": f"{label} · {DATA_SOURCE_NOTE}",
                    "location": "",
                    "start_date": start,
                    "end_date": end,
                    "all_day": True,
                    "is_range": True,
                    "cancelled": False,
                })
    return events


def _next_day(day: date) -> date:
    from datetime import timedelta
    return day + timedelta(days=1)


def _previous_day(day: date) -> date:
    from datetime import timedelta
    return day - timedelta(days=1)
