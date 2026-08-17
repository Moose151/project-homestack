"""Australian public holidays, as published by the jurisdiction that declares them.

Every date here is an explicit, dated entry taken from the responsible government's own
published list. Nothing is derived.

That is a deliberate reversal of the previous approach, which built a "national" list and then
layered per-state rules on top. It produced confidently wrong answers, because the premise is
false — there is no national public holiday list in Australia. Each state and territory
declares its own, and they disagree about which days exist at all (Easter Sunday is a public
holiday in some jurisdictions and not others), about substitution (Queensland moves Anzac Day
when it falls on a Sunday but not a Saturday; other jurisdictions differ), and about names
("the day after Good Friday", not "Easter Saturday"). Only explicit published data is safe.

**Coverage is deliberately limited to what has been verified.** Queensland is supported for
2026 and 2027, checked against qld.gov.au's own public-holiday and show-holiday pages. Other
states and territories are *not* offered rather than shipped with unverified dates — see
``SUPPORTED_REGIONS`` and docs/38 §11 for how to add one.

Verified against:
  - https://www.qld.gov.au/recreation/travel/holidays/public          (2026, 2027)
  - https://www.qld.gov.au/recreation/travel/holidays/show            (2026 show holidays)
Last checked: 2026-08-17.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time

DATA_SOURCE_NOTE = "Queensland Government published public holiday dates"
DATA_CHECKED_ON = "2026-08-17"

NATIONAL = "national"
REGIONAL = "regional"
LOCAL = "local"

# Only jurisdictions with verified data are offered. Adding one means adding its published
# dates below and listing it here — never enabling it and hoping.
SUPPORTED_REGIONS = ("QLD",)
DATA_YEARS = (2026, 2027)


@dataclass(frozen=True)
class Holiday:
    name: str
    day: date
    scope: str
    jurisdiction: str
    # Queensland's Christmas Eve holiday runs 6pm–midnight. Representing it as all-day would
    # tell the household the whole day is a holiday, which is simply untrue.
    starts_at: time | None = None
    ends_at: time | None = None

    @property
    def is_part_day(self) -> bool:
        return self.starts_at is not None


_PART_EVENING = (time(18, 0), time(23, 59))

# --- Queensland -----------------------------------------------------------------------------
# State-wide holidays. Substitute days appear as their own entries exactly as gazetted, rather
# than being computed from a weekend rule that differs per holiday and per jurisdiction.
_QLD: dict[int, list[Holiday]] = {
    2026: [
        Holiday("New Year's Day", date(2026, 1, 1), REGIONAL, "QLD"),
        Holiday("Australia Day", date(2026, 1, 26), REGIONAL, "QLD"),
        Holiday("Good Friday", date(2026, 4, 3), REGIONAL, "QLD"),
        Holiday("The day after Good Friday", date(2026, 4, 4), REGIONAL, "QLD"),
        Holiday("Easter Sunday", date(2026, 4, 5), REGIONAL, "QLD"),
        Holiday("Easter Monday", date(2026, 4, 6), REGIONAL, "QLD"),
        # 25 April 2026 is a Saturday. Queensland grants no substitute in that case.
        Holiday("Anzac Day", date(2026, 4, 25), REGIONAL, "QLD"),
        Holiday("Labour Day", date(2026, 5, 4), REGIONAL, "QLD"),
        Holiday("King's Birthday", date(2026, 10, 5), REGIONAL, "QLD"),
        Holiday("Christmas Eve (from 6pm)", date(2026, 12, 24), REGIONAL, "QLD", *_PART_EVENING),
        Holiday("Christmas Day", date(2026, 12, 25), REGIONAL, "QLD"),
        Holiday("Boxing Day", date(2026, 12, 26), REGIONAL, "QLD"),
        Holiday("Boxing Day (additional)", date(2026, 12, 28), REGIONAL, "QLD"),
    ],
    2027: [
        Holiday("New Year's Day", date(2027, 1, 1), REGIONAL, "QLD"),
        Holiday("Australia Day", date(2027, 1, 26), REGIONAL, "QLD"),
        Holiday("Good Friday", date(2027, 3, 26), REGIONAL, "QLD"),
        Holiday("The day after Good Friday", date(2027, 3, 27), REGIONAL, "QLD"),
        Holiday("Easter Sunday", date(2027, 3, 28), REGIONAL, "QLD"),
        Holiday("Easter Monday", date(2027, 3, 29), REGIONAL, "QLD"),
        # 25 April 2027 is a Sunday, and Queensland *does* substitute in that case.
        Holiday("Anzac Day", date(2027, 4, 26), REGIONAL, "QLD"),
        Holiday("Labour Day", date(2027, 5, 3), REGIONAL, "QLD"),
        Holiday("King's Birthday", date(2027, 10, 4), REGIONAL, "QLD"),
        Holiday("Christmas Eve (from 6pm)", date(2027, 12, 24), REGIONAL, "QLD", *_PART_EVENING),
        Holiday("Christmas Day", date(2027, 12, 25), REGIONAL, "QLD"),
        Holiday("Christmas Day (additional)", date(2027, 12, 27), REGIONAL, "QLD"),
        Holiday("Boxing Day", date(2027, 12, 26), REGIONAL, "QLD"),
        Holiday("Boxing Day (additional)", date(2027, 12, 28), REGIONAL, "QLD"),
    ],
}

REGION_HOLIDAYS: dict[str, dict[int, list[Holiday]]] = {"QLD": _QLD}

# --- Local show holidays --------------------------------------------------------------------
# Declared per district, which is why Household.locality exists. The Royal Queensland Show is
# a Brisbane-area holiday, not a state-wide one, and is filed here accordingly.
LOCAL_HOLIDAYS: dict[str, dict[int, list[Holiday]]] = {
    "brisbane": {
        2026: [Holiday("Royal Queensland Show (Ekka)", date(2026, 8, 12), LOCAL, "brisbane")],
        2027: [Holiday("Royal Queensland Show (Ekka)", date(2027, 8, 11), LOCAL, "brisbane")],
    },
    "gold_coast": {
        2026: [Holiday("Gold Coast Show", date(2026, 8, 28), LOCAL, "gold_coast")],
    },
    "toowoomba": {
        2026: [Holiday("Toowoomba Royal Agricultural Show", date(2026, 3, 27), LOCAL, "toowoomba")],
    },
    "cairns": {
        2026: [Holiday("Cairns Annual Show", date(2026, 7, 17), LOCAL, "cairns")],
    },
    "townsville": {
        2026: [Holiday("Townsville Annual Show", date(2026, 7, 6), LOCAL, "townsville")],
    },
}

# locality slug -> (owning region, display name). A locality is only honoured inside its own
# region, so a stale locality left after moving interstate cannot inject the old show day.
LOCALITIES = {
    "brisbane": ("QLD", "Brisbane"),
    "gold_coast": ("QLD", "Gold Coast"),
    "toowoomba": ("QLD", "Toowoomba"),
    "cairns": ("QLD", "Cairns"),
    "townsville": ("QLD", "Townsville"),
}


def is_supported_region(region: str) -> bool:
    return (region or "").upper() in SUPPORTED_REGIONS


def holidays_for(*, year: int, state: str = "", locality: str = "",
                 include_national: bool = True, include_regional: bool = True,
                 include_local: bool = True) -> list[Holiday]:
    """Every published holiday that applies to one jurisdiction in one year.

    ``include_national`` is accepted for API compatibility but selects nothing on its own: in
    Australia there is no separate national list to include — the days people think of as
    national (Christmas, Anzac Day) are declared by each state, and are already in its list.
    """
    region = (state or "").upper()
    locality = (locality or "").lower()
    out: list[Holiday] = []

    if include_regional and region in REGION_HOLIDAYS:
        out.extend(REGION_HOLIDAYS[region].get(year, []))

    if include_local and locality:
        owner_region = LOCALITIES.get(locality, ("", ""))[0]
        if not region or owner_region == region:
            out.extend(LOCAL_HOLIDAYS.get(locality, {}).get(year, []))

    return sorted(out, key=lambda entry: (entry.day, entry.name))


def build_events(source, *, household, years: tuple[int, ...] = ()) -> list[dict]:
    """Normalised event dicts for the sync layer.

    The UID embeds jurisdiction, date and name, so re-running a year updates its entries rather
    than appending a second copy, and a household that changes state stops matching the old
    jurisdiction's UIDs.
    """
    from datetime import datetime

    settings = source.settings_json or {}
    state = (household.region or "").upper()
    locality = (household.locality or "").lower()
    span = years or _default_years()

    events: list[dict] = []
    for year in span:
        for holiday in holidays_for(
            year=year,
            state=state,
            locality=locality,
            include_national=settings.get("include_national", True),
            include_regional=settings.get("include_regional", True),
            include_local=settings.get("include_local", True),
        ):
            entry = {
                "uid": f"auhol-{holiday.scope}-{holiday.jurisdiction}-{holiday.day.isoformat()}-{_slug(holiday.name)}",
                "summary": holiday.name,
                "description": (
                    f"{'Local' if holiday.scope == LOCAL else 'Queensland'} public holiday"
                    f" · {DATA_SOURCE_NOTE}"
                ),
                "location": "",
                "is_range": False,
                "cancelled": False,
            }
            if holiday.is_part_day:
                # A part-day holiday is a timed entry, because it genuinely is one.
                entry["start_at"] = datetime.combine(holiday.day, holiday.starts_at)
                entry["end_at"] = datetime.combine(holiday.day, holiday.ends_at)
                entry["all_day"] = False
            else:
                entry["start_date"] = holiday.day
                entry["end_date"] = holiday.day
                entry["all_day"] = True
            events.append(entry)
    return events


def _default_years() -> tuple[int, ...]:
    """This year and next, clipped to the years actually published here.

    Producing nothing for an unpublished year is the correct behaviour: an empty calendar is
    honest, a guessed one is not.
    """
    from django.utils import timezone

    this_year = timezone.localdate().year
    return tuple(year for year in (this_year, this_year + 1) if year in DATA_YEARS)


def _slug(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")
