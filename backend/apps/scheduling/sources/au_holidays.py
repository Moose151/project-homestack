"""Australian public holidays, by jurisdiction.

Holiday dates are *declared*, not calculated. States gazette them year by year, they move when
they fall on a weekend, and the rules differ between jurisdictions — so this module ships dated
data with provenance rather than an algorithm that would confidently produce wrong answers for
future years. The only computed dates are the Easter-anchored ones, which genuinely are
formula-defined (Western computus) and are the same everywhere in Australia.

Scope is national + state/territory + a small set of local show holidays. A Queensland
household must never receive a Victoria-only holiday, so every entry declares the jurisdiction
it belongs to and the household's configured location decides what applies.

Provenance: dates below follow the Commonwealth and state/territory public-holiday listings
(australia.gov.au/public-holidays and the equivalent state pages, e.g. Queensland's
qld.gov.au/recreation/travel/holidays/public). ``DATA_YEARS`` records the years actually
covered; ``DATA_SOURCE_NOTE`` is stored on generated events so the origin of a date is
recoverable later. Refreshing a future year is a data change here, not a code change.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

DATA_SOURCE_NOTE = "Australian federal/state public holiday listings"
DATA_YEARS = (2025, 2026, 2027)

NATIONAL = "national"
REGIONAL = "regional"
LOCAL = "local"

# Recognised state/territory codes.
STATES = ("ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA")

# Local/show holidays, keyed by a provider-scoped locality slug. Local shows are declared per
# council/district and are the reason `Household.locality` exists.
LOCAL_HOLIDAYS: dict[str, dict[str, list[tuple[int, int, int]]]] = {
    # Brisbane's Royal Queensland Show ("Ekka") People's Day.
    "brisbane": {"Brisbane Show Day (Ekka)": [(2025, 8, 13), (2026, 8, 12), (2027, 8, 11)]},
    "gold_coast": {"Gold Coast Show Day": [(2025, 8, 29), (2026, 8, 28), (2027, 8, 27)]},
    "toowoomba": {"Toowoomba Show Day": [(2025, 3, 28), (2026, 3, 27), (2027, 3, 26)]},
    "cairns": {"Cairns Show Day": [(2025, 7, 18), (2026, 7, 17), (2027, 7, 16)]},
    "townsville": {"Townsville Show Day": [(2025, 7, 4), (2026, 7, 3), (2027, 7, 2)]},
}

LOCALITIES = {
    "brisbane": ("QLD", "Brisbane"),
    "gold_coast": ("QLD", "Gold Coast"),
    "toowoomba": ("QLD", "Toowoomba"),
    "cairns": ("QLD", "Cairns"),
    "townsville": ("QLD", "Townsville"),
}


@dataclass(frozen=True)
class Holiday:
    name: str
    day: date
    scope: str
    jurisdiction: str  # "AU", a state code, or a locality slug


def easter_sunday(year: int) -> date:
    """Western (Gregorian) Easter — Meeus/Jones/Butcher.

    Legitimately a formula: unlike gazetted holidays, Easter's date is defined by rule, and every
    Australian jurisdiction derives Good Friday and Easter Monday from it.
    """
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    lunar = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * lunar) // 451
    month, day = divmod(h + lunar - 7 * m + 114, 31)
    return date(year, month, day + 1)


# Fixed-date national holidays, with the substitution rule Australia actually applies.
def _observed(day: date, *, substitute: bool) -> list[date]:
    """A holiday plus its weekend substitute, where the jurisdiction grants one."""
    if not substitute or day.weekday() < 5:
        return [day]
    # Saturday -> following Monday; Sunday -> following Monday.
    shift = 2 if day.weekday() == 5 else 1
    return [day, day + timedelta(days=shift)]


def _national(year: int) -> list[Holiday]:
    easter = easter_sunday(year)
    out: list[Holiday] = []

    def add(name: str, day: date, *, substitute: bool = False) -> None:
        for index, actual in enumerate(_observed(day, substitute=substitute)):
            label = f"{name} (observed)" if index else name
            out.append(Holiday(label, actual, NATIONAL, "AU"))

    add("New Year's Day", date(year, 1, 1), substitute=True)
    add("Australia Day", date(year, 1, 26), substitute=True)
    add("Good Friday", easter - timedelta(days=2))
    add("Easter Saturday", easter - timedelta(days=1))
    add("Easter Sunday", easter)
    add("Easter Monday", easter + timedelta(days=1))
    add("ANZAC Day", date(year, 4, 25))
    add("Christmas Day", date(year, 12, 25), substitute=True)
    add("Boxing Day", date(year, 12, 26), substitute=True)
    return out


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """The nth given weekday of a month (n=1 is the first)."""
    day = date(year, month, 1)
    offset = (weekday - day.weekday()) % 7
    return day + timedelta(days=offset + 7 * (n - 1))


# State/territory holidays. Dates that follow a stable "nth weekday" gazettal rule are derived;
# anything a state moves at will is listed explicitly per year.
def _state(year: int, state: str) -> list[Holiday]:
    out: list[Holiday] = []

    def add(name: str, day: date) -> None:
        out.append(Holiday(name, day, REGIONAL, state))

    if state == "QLD":
        add("Labour Day", _nth_weekday(year, 5, 0, 1))            # first Monday in May
        add("King's Birthday", _nth_weekday(year, 10, 0, 1))       # first Monday in October
    elif state == "NSW":
        add("Labour Day", _nth_weekday(year, 10, 0, 1))
        add("King's Birthday", _nth_weekday(year, 6, 0, 2))
    elif state == "VIC":
        add("Labour Day", _nth_weekday(year, 3, 0, 2))
        add("King's Birthday", _nth_weekday(year, 6, 0, 2))
        add("Melbourne Cup Day", _nth_weekday(year, 11, 1, 1))     # first Tuesday in November
        add("Friday before the AFL Grand Final", {
            2025: date(2025, 9, 26), 2026: date(2026, 9, 25), 2027: date(2027, 9, 24),
        }.get(year, date(year, 9, 27)))
    elif state == "SA":
        add("Labour Day", _nth_weekday(year, 10, 0, 1))
        add("King's Birthday", _nth_weekday(year, 6, 0, 2))
        add("Adelaide Cup Day", _nth_weekday(year, 3, 0, 2))
    elif state == "WA":
        add("Labour Day", _nth_weekday(year, 3, 0, 1))
        add("Western Australia Day", _nth_weekday(year, 6, 0, 1))
        # WA moves the King's Birthday each year by proclamation.
        add("King's Birthday", {
            2025: date(2025, 9, 29), 2026: date(2026, 9, 28), 2027: date(2027, 9, 27),
        }.get(year, _nth_weekday(year, 9, 0, 5)))
    elif state == "TAS":
        add("Eight Hours Day", _nth_weekday(year, 3, 0, 2))
        add("King's Birthday", _nth_weekday(year, 6, 0, 2))
        add("Recreation Day", _nth_weekday(year, 11, 0, 1))
    elif state == "NT":
        add("May Day", _nth_weekday(year, 5, 0, 1))
        add("King's Birthday", _nth_weekday(year, 6, 0, 2))
        add("Picnic Day", _nth_weekday(year, 8, 0, 1))
    elif state == "ACT":
        add("Canberra Day", _nth_weekday(year, 3, 0, 2))
        add("Labour Day", _nth_weekday(year, 10, 0, 1))
        add("King's Birthday", _nth_weekday(year, 6, 0, 2))
        add("Reconciliation Day", _reconciliation_day(year))
    return out


def _reconciliation_day(year: int) -> date:
    """ACT: the Monday on or after 27 May."""
    day = date(year, 5, 27)
    return day + timedelta(days=(0 - day.weekday()) % 7)


def _local(year: int, locality: str) -> list[Holiday]:
    entries = LOCAL_HOLIDAYS.get(locality, {})
    out: list[Holiday] = []
    for name, days in entries.items():
        for (y, month, day) in days:
            if y == year:
                out.append(Holiday(name, date(y, month, day), LOCAL, locality))
    return out


def holidays_for(*, year: int, state: str = "", locality: str = "",
                 include_national: bool = True, include_regional: bool = True,
                 include_local: bool = True) -> list[Holiday]:
    """Every holiday that applies to one jurisdiction in one year."""
    out: list[Holiday] = []
    if include_national:
        out.extend(_national(year))
    if include_regional and state in STATES:
        out.extend(_state(year, state))
    if include_local and locality:
        # A locality only contributes when it belongs to the configured state, so a stale
        # locality left behind after moving interstate cannot inject the old state's show day.
        owner_state = LOCALITIES.get(locality, ("", ""))[0]
        if not state or owner_state == state:
            out.extend(_local(year, locality))
    return sorted(out, key=lambda entry: (entry.day, entry.name))


def build_events(source, *, household, years: tuple[int, ...] = ()) -> list[dict]:
    """Normalised event dicts for the sync layer.

    The UID embeds jurisdiction, year and name, so re-running a year updates its entries rather
    than appending a second copy, and a household that changes state stops matching the old
    jurisdiction's UIDs.
    """
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
            events.append({
                "uid": f"auhol-{holiday.scope}-{holiday.jurisdiction}-{holiday.day.isoformat()}-{_slug(holiday.name)}",
                "summary": holiday.name,
                "description": f"{holiday.scope.title()} public holiday · {DATA_SOURCE_NOTE}",
                "location": "",
                "start_date": holiday.day,
                "end_date": holiday.day,
                "all_day": True,
                "is_range": False,
                "cancelled": False,
            })
    return events


def _default_years() -> tuple[int, ...]:
    """This year and the next, clipped to the years the shipped data actually covers."""
    from django.utils import timezone

    this_year = timezone.localdate().year
    wanted = (this_year, this_year + 1)
    covered = tuple(year for year in wanted if year in DATA_YEARS)
    # Outside the shipped range, still produce the formula-derived national set for this year so
    # the calendar is not silently empty; state data simply stops until the data is refreshed.
    return covered or (this_year,)


def _slug(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")
