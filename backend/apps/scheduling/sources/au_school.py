"""Australian school terms and holidays, as published by each education department.

Two things this module refuses to guess.

**Systems, not states.** Catholic and independent schools routinely differ from the state
system by a day or more at each boundary, so a "Queensland schools" calendar would be wrong for
a large minority of Queensland families. Only named systems with published dates are offered;
anything else belongs in a subscribed ICS feed from the school itself.

**Student dates, not staff dates.** NSW terms begin with school development days *before*
students return, and NSW additionally splits into an Eastern and a Western division whose
students start on different days — in 2026, 2 February and 9 February respectively. Using the
development-day date (27 January) as a term start, as an earlier version did, tells a family
their children are at school a week before they are.

Coverage is deliberately limited to verified data. A system/year that is not published here
simply produces nothing, which is honest; a guessed term date is not.

Verified against:
  - https://education.qld.gov.au/about-us/calendar/term-dates       (QLD 2026)
  - https://education.qld.gov.au/about-us/calendar/future-dates     (QLD 2027)
  - https://education.nsw.gov.au/schooling/calendars/2026           (NSW 2026, both divisions)
Last checked: 2026-08-17.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

DATA_SOURCE_NOTE = "State education department published term dates"
DATA_CHECKED_ON = "2026-08-17"

# system slug -> (label, state)
SCHOOL_SYSTEMS = {
    "qld_state": ("Queensland State Schools", "QLD"),
    "nsw_state_eastern": ("NSW Public Schools (Eastern division)", "NSW"),
    "nsw_state_western": ("NSW Public Schools (Western division)", "NSW"),
}


@dataclass(frozen=True)
class Term:
    number: int
    start: date
    end: date


# system -> year -> student term dates. Staff/development days are deliberately excluded: they
# are not when students attend, and student-free day data is not implemented (see below).
TERMS: dict[str, dict[int, list[Term]]] = {
    "qld_state": {
        2026: [
            Term(1, date(2026, 1, 27), date(2026, 4, 2)),
            Term(2, date(2026, 4, 20), date(2026, 6, 26)),
            Term(3, date(2026, 7, 13), date(2026, 9, 18)),
            Term(4, date(2026, 10, 6), date(2026, 12, 11)),
        ],
        2027: [
            Term(1, date(2027, 1, 27), date(2027, 3, 25)),
            Term(2, date(2027, 4, 12), date(2027, 6, 25)),
            Term(3, date(2027, 7, 12), date(2027, 9, 17)),
            Term(4, date(2027, 10, 5), date(2027, 12, 10)),
        ],
    },
    # NSW divisions share every boundary except the Term 1 student start: Western division
    # ("late start") students return a week later.
    "nsw_state_eastern": {
        2026: [
            Term(1, date(2026, 2, 2), date(2026, 4, 2)),
            Term(2, date(2026, 4, 22), date(2026, 7, 3)),
            Term(3, date(2026, 7, 21), date(2026, 9, 25)),
            Term(4, date(2026, 10, 13), date(2026, 12, 17)),
        ],
    },
    "nsw_state_western": {
        2026: [
            Term(1, date(2026, 2, 9), date(2026, 4, 2)),
            Term(2, date(2026, 4, 22), date(2026, 7, 3)),
            Term(3, date(2026, 7, 21), date(2026, 9, 25)),
            Term(4, date(2026, 10, 13), date(2026, 12, 17)),
        ],
    },
}

# Student-free / pupil-free day data is not implemented. The toggle exists in the model, but no
# provider supplies these dates, so it stays off and produces nothing rather than silently
# meaning something else.
STUDENT_FREE_DAYS: dict[str, dict[int, list[date]]] = {}


def system_label(system: str) -> str:
    return SCHOOL_SYSTEMS.get(system, (system, ""))[0]


def terms_for(system: str, year: int) -> list[Term]:
    return TERMS.get(system, {}).get(year, [])


def build_events(source, *, household, years: tuple[int, ...] = ()) -> list[dict]:
    """Term and break ranges for the configured school system.

    Breaks are derived from the gap between consecutive terms — that *is* what a school holiday
    is, and deriving it avoids a second table that could disagree with the first. The break
    after the final term is only produced when the following year's Term 1 is published, so a
    summer break never runs off into an invented date.
    """
    from django.utils import timezone

    settings = source.settings_json or {}
    system = settings.get("system", "")
    show_terms = settings.get("show_terms", True)
    show_holidays = settings.get("show_holidays", True)
    show_student_free = settings.get("show_student_free", False)

    this_year = timezone.localdate().year
    span = years or (this_year, this_year + 1)
    label = system_label(system)

    events: list[dict] = []
    for year in span:
        terms = terms_for(system, year)
        if not terms:
            continue

        if show_terms:
            for term in terms:
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
            following = terms_for(system, year + 1)
            boundaries = list(zip(terms, terms[1:]))
            if following:
                boundaries.append((terms[-1], following[0]))
            for earlier, later in boundaries:
                start = earlier.end + timedelta(days=1)
                end = later.start - timedelta(days=1)
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

        if show_student_free:
            for day in STUDENT_FREE_DAYS.get(system, {}).get(year, []):
                events.append({
                    "uid": f"auschool-{system}-{day.isoformat()}-studentfree",
                    "summary": "Student-free day",
                    "description": f"{label} · {DATA_SOURCE_NOTE}",
                    "location": "",
                    "start_date": day,
                    "end_date": day,
                    "all_day": True,
                    "is_range": False,
                    "cancelled": False,
                })

    return events
