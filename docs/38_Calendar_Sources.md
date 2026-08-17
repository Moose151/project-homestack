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
| `url` | fetched sources only; `webcal://` is normalised to `https://` |
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

`event.is_source_managed` drives the read-only treatment in the UI.

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

Holiday dates are **declared, not calculated**. Governments gazette them year by year and move
them when they fall on a weekend, and the rules differ per jurisdiction. So dates ship as data
with provenance (`apps/scheduling/sources/au_holidays.py`, `DATA_SOURCE_NOTE`, `DATA_YEARS`).

The only computed dates are Easter-anchored (Good Friday, Easter Saturday/Sunday/Monday), which
genuinely are formula-defined and identical Australia-wide, plus stable "nth weekday of month"
gazettal rules where a state actually uses one.

Levels are distinguished and independently switchable: `national`, `regional`, `local`.

School terms live in `au_school.py`, keyed by **system** rather than state — Catholic and
independent schools frequently differ from the state system by a day or more, so pretending one
set of dates covers a whole state would quietly be wrong. Terms and breaks are single **ranges**;
generating an event per day would bury eleven weeks of calendar.

**Refreshing a future year is a data change in these modules, not a code change.** Re-running a
year updates its entries rather than appending duplicates, because the UID embeds jurisdiction,
year and name.

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

Validation happens at both save and fetch time. **Residual risk:** a DNS-rebinding window
remains between the final resolution check and the socket connect. Closing it entirely requires
pinning the connection to the validated IP while preserving TLS SNI and certificate validation;
that is deliberately not implemented yet and is recorded here rather than left implicit.

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
- source-managed entries are **read-only** in the edit form: they open a detail panel naming the
  source and linking to its settings, rather than pretending an edit would survive the next sync
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
| holidays missing for a state | household `region` unset, or the year is outside `DATA_YEARS` |
| no local show day | `locality` unset, or it belongs to a different `region` |
| school dates absent | that system/year is not in `TERMS` yet |
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
