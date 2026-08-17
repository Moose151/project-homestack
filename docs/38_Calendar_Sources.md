# 38 — Calendar Sources

How HomeStack shows dates it does not own: public holidays, school terms, and calendars
published by someone else.

---

## 1. Why this exists

Before this, every dated thing in HomeStack was either a hand-made event or a node record
mirrored into the Calendar. Public holidays, school terms and a club's fixture list are none of
those. They share one shape instead:

- someone else owns the dates;
- HomeStack mirrors them;
- the mirror must survive being refreshed, repeatedly, without duplicating or losing anything.

Modelling that once means a new provider is a new row plus a provider module — not another
Calendar redesign.

```
Calendar
├── HomeStack          events, appointments, reminders (unchanged)
├── Automatic          public/regional/local holidays, school terms and breaks
└── Subscribed         ICS/webcal feeds, and one-time .ics imports
```

---

## 2. The model

`scheduling.CalendarSource`

| Field | Meaning |
| --- | --- |
| `kind` | how it is fed: `holidays`, `school`, `subscription`, `import` |
| `provider` | who feeds it: `au_holidays`, `au_school_terms`, `ics` |
| `name`, `colour`, `category` | presentation |
| `is_enabled` | off hides its entries everywhere, without deleting them |
| `url` | fetched sources only; `webcal://` normalised to `https://`. **Never serialised back** — see §6 |
| `settings_json` | **validated per provider** — never free JSON |
| `show_on_calendar` / `show_in_upcoming` | independent visibility switches |
| `notifications_enabled` | **defaults off** |
| `last_sync_at`, `last_success_at`, `sync_status`, `sync_error` | operator visibility |
| `sync_revision` | monotonic; how disappearance is detected |

`(kind, provider)` must exist in `apps/scheduling/sources/registry.py`. Anything else is
rejected. `settings_json` is validated by that provider's own validator before it is stored,
because those values decide what the server fetches and which jurisdiction's dates are produced.

### Source-managed events

`CalendarEvent` gains mirror metadata, all empty for hand-made events:

| Field | Meaning |
| --- | --- |
| `calendar_source` | owning source (cascade delete) |
| `external_uid` | the feed's UID, or a provider-derived stable key |
| `external_sequence` | iCalendar `SEQUENCE`, when present |
| `last_seen_revision` | the sync revision this entry was last seen in |
| `is_range` | a multi-day banner (school term/break) rather than a timed entry |

`event.is_source_managed` drives the read-only treatment in the UI;
`event.is_externally_managed` (`is_synced or is_source_managed`) is what every **write path**
checks, in the view *and* the service layer.

---

## 3. Household location

Holidays are jurisdictional, so `core.Household` carries:

- `country` — ISO-3166-1 alpha-2 (`AU`)
- `region` — state/territory code (`QLD`)
- `locality` — provider-scoped slug (`brisbane`)
- `postcode` — reserved for finer providers later
- `timezone` — already existed

Set in **Settings → Household → Location**.

> These are calendar configuration. Nothing derives permissions or any security decision from
> them.

A locality is only honoured when it belongs to the configured region, so a stale locality left
behind after moving interstate cannot inject the old state's show day.

---

## 4. Holiday and school data

Every date is an **explicit, dated entry copied from the responsible government's published
list**. Nothing is derived.

That is deliberate. An earlier version built a "national" list and layered per-state rules on
top, and it was confidently wrong, because the premise is false: **there is no national public
holiday list in Australia.** Each state and territory declares its own, and they disagree about

- *which days exist* — Easter Sunday is a public holiday in some jurisdictions, not others;
- *substitution* — Queensland moves Anzac Day when 25 April is a Sunday but **not** a Saturday;
- *naming* — Queensland gazettes "the day after Good Friday", not "Easter Saturday";
- *part-days* — Queensland's Christmas Eve holiday runs 6pm–midnight and is stored as a timed
  entry, because saying the whole day is a holiday would be untrue.

### Verified coverage

Coverage is limited to what has actually been checked against the source, and unsupported
jurisdictions produce **nothing** rather than borrowing another state's dates.

| Provider | Covers | Verified against | Checked |
| --- | --- | --- | --- |
| `au_holidays` | **QLD only**, 2026–2027 | qld.gov.au public-holiday and show-holiday pages | 2026-08-17 |
| `au_school_terms` | QLD state 2026–2027; NSW public (Eastern **and** Western) 2026 | education.qld.gov.au, education.nsw.gov.au | 2026-08-17 |

Other states and territories are not offered. Enabling one means adding its published dates and
listing it in `SUPPORTED_REGIONS` / `SCHOOL_SYSTEMS` — never flipping a flag and hoping.

School data is keyed by **system**, not state: Catholic and independent schools routinely differ
from the state system, and NSW additionally splits into Eastern and Western divisions whose
students return on different days (2 February and 9 February in 2026). Term boundaries use
**student** dates — an earlier version used NSW's school-development day (27 January), which
tells a family their children are at school a week before they are.

Student-free/pupil-free days are **not implemented**. The toggle exists but no provider supplies
the dates, so it stays off and produces nothing rather than quietly meaning something else.

Terms and breaks are single **ranges**; an event per day would bury eleven weeks of calendar.
A break is derived from the gap between consecutive terms, and the summer break is only produced
once the following year's Term 1 is published, so nothing runs off into an invented date.

**Refreshing a future year is a data change in these modules, not a code change.** Re-running a
year updates its entries rather than appending duplicates, because the UID embeds jurisdiction,
date and name.

---

## 5. ICS subscriptions and imports

**Subscribe** — stores a URL, refreshed on a schedule.
**Import** — reads a posted `.ics` once; `can_sync` is false and a later sync is a no-op.

Both parse through `apps/scheduling/sources/ics.py`, a small RFC 5545 reader covering `UID`,
`DTSTART`/`DTEND` (including `VALUE=DATE` and `TZID`), `SUMMARY`, `DESCRIPTION`, `LOCATION`,
`STATUS`, `SEQUENCE`, `RRULE`, `RDATE`/`EXDATE`, line folding and text escaping. It produces
**data only** — text is unescaped into plain strings and never treated as HTML or markup.

### Sync semantics

Identity is `(calendar_source, external_uid)`.

| Situation | Result |
| --- | --- |
| same UID, changed `DTSTART` | existing entry moves |
| same UID, changed title/venue | existing entry updates |
| same UID, synced repeatedly | one entry; converges |
| `STATUS:CANCELLED` | entry removed |
| all-day entry | stays all-day; exclusive `DTEND` converted to inclusive |
| floating time (no TZID/Z) | anchored to the household timezone |
| entry no longer in the feed | **future** entries removed; **past** entries kept |

That last row is the deliberate conservative policy: a feed that publishes only the current
season must not erase the household's record of the last one.

---

## 6. Network security (SSRF)

HomeStack is LAN-hosted beside Postgres, the backend and a reverse proxy. Fetching a
user-supplied URL *from the server* is a real SSRF surface, so
`apps/scheduling/sources/fetching.py` **fails closed**.

- scheme allowlist: `http`, `https`; `webcal`/`webcals` normalised to `https`
- URLs carrying credentials are refused rather than silently stripped
- **every** resolved address must be public — a name answering with one public and one private
  address is refused outright, not load-balanced into
- refused ranges: loopback, RFC1918 private, link-local (covers `169.254.169.254` cloud
  metadata), multicast, reserved, unspecified; IPv4-mapped, 6to4 and Teredo IPv6 forms are
  unwrapped first so `::ffff:127.0.0.1` cannot launder loopback
- redirects are **not followed by urllib** — each hop is returned to the caller and re-validated
  before the next request (max 3)
- connect/read timeouts, a 5 MB response cap enforced *while reading*, and a 2000-event cap
- a response without `BEGIN:VCALENDAR` is rejected
- destinations are validated when a subscription is **saved**, not only when fetched

### The connection is pinned to the validated address

Resolving a name, approving the answer, then handing the *hostname* to an HTTP library lets that
library resolve it again and connect somewhere else — DNS rebinding, against which
pre-validation is worthless. So the flow is always:

```
resolve once  ->  validate every answer  ->  connect the socket to one validated address
```

`_PinnedHTTPConnection` / `_PinnedHTTPSConnection` open the socket on the validated IP while
leaving the hostname in place for **SNI, certificate verification and the `Host` header**.
Pinning therefore costs nothing in TLS security: a certificate valid for the hostname is still
required. Each redirect hop repeats the whole cycle independently.

A regression test flips DNS to a private address after validation and asserts the socket still
went to the validated public one.

### ICS subscription URLs are secrets

A subscription link routinely carries a per-user token (`...?key=abc123`), which is a bearer
credential for that person's calendar. The stored URL is therefore **never serialised back**.
The API exposes only `has_url` and `url_display` (host only — never the path or query, where
tokens live). A manager replaces a link by sending a new one; nobody needs the old one returned.
Sync errors are redacted before being stored, since a networking exception may quote the URL.

Feed content is never executed or rendered as trusted HTML.

---

## 7. Scheduled refresh

```
17 */3 * * * docker exec homestack-backend python manage.py calendar_sync_sources
```

- `--interval-hours N` skips sources refreshed successfully within N hours (default 6)
- `--force` refreshes every enabled source
- idempotent: identity is the UID, and each source is row-locked so concurrent runs serialise
- one source failing is recorded on its own row and never aborts the run
- **external HTTP never happens during a page load** — only here, or via explicit *Sync now*

A few hours is ample for fixture lists and school calendars. Polling harder is rude to the
provider and buys nothing.

---

## 8. Display, Dashboard and notifications

- each source is its own filter layer on the Calendar (Month/Week/Day/Agenda), coloured by the
  source; "HomeStack" is the layer for the household's own events
- source-managed entries are **read-only**, and not merely in the UI: `PATCH` and `DELETE` on the
  events API refuse them at both the view and the service layer. `CalendarEvent.is_externally_managed`
  is the single question every write path asks — `is_synced` alone missed them, because a
  source-managed entry leaves `source_record_*` empty
- a disabled or calendar-hidden source is excluded from **global search** as well as the
  calendar, so "disabled" means disabled everywhere the household looks
- `show_in_upcoming` controls Dashboard Upcoming independently of `show_on_calendar`
- **notifications default off.** Source-managed entries otherwise look like standalone events to
  the notification sweep, which would have announced every fixture in a subscribed season
- holidays and fixtures are events, so they use event wording — "Today", "Tomorrow",
  "Starts at 7:50 PM" — and never "Due"/"Overdue" (see docs/32 §8)

---

## 9. Permissions

Reuses the seeded scheduling permissions rather than inventing a new action:

| Action | Permission | Roles |
| --- | --- | --- |
| view sources | `scheduling.view` | everyone |
| add | `scheduling.create` | admin, manager |
| change / sync | `scheduling.edit` | admin, manager |
| remove | `scheduling.delete` | admin, manager |

Enforced in the API, not by hiding buttons.

---

## 10. Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| "points inside the local network" | the URL resolves to a private/loopback/link-local address |
| "did not return a calendar file" | the URL serves HTML (a login page or a share link, not the ICS) |
| "too large to import" | over the 5 MB cap |
| no holidays at all | `region` is not QLD — other states are not supported yet (§4) |
| holidays missing for a year | outside the verified `DATA_YEARS` (2026–2027) |
| no local show day | `locality` unset, or it belongs to a different `region` |
| school dates absent | that system/year is not in `TERMS` yet (§4 lists what is verified) |
| NSW dates a week out | the wrong division is selected — Eastern and Western start differently |
| nothing refreshes | the cron entry is missing; check `last_sync_at`/`sync_error` |

---

## 11. Adding another country or provider

1. Write a module in `apps/scheduling/sources/` exposing
   `build_events(source, *, household, years=()) -> list[dict]` with normalised entries
   (`uid`, `summary`, `description`, `location`, `start_date`/`start_at`, `end_date`/`end_at`,
   `all_day`, `is_range`, `cancelled`).
2. Register `(kind, provider)` in `registry.PROVIDERS` with a settings validator, category,
   colour and whether it needs a URL.
3. Map it in `registry.provider_for`.
4. Add jurisdiction tests, including one proving a neighbouring jurisdiction's dates do not leak.

The sync loop, UID semantics, visibility switches, permissions and UI need no changes.

**Not implemented (deliberately):** Google/Microsoft OAuth sync, CalDAV two-way sync,
authenticated feeds, per-school bespoke integrations, and editing subscribed entries locally.
