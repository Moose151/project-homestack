# Core Spec — Calendar

> **Status:** shipped core service and in daily use. The Django app is `scheduling` (D16).
> Calendar is the household timeline; node records own their semantic dates and project into it
> through the shared scheduling helper (D7). Appointments, Atlas Agenda integration and generic
> rotating schedules are already shipped.

## 1. Purpose

Calendar answers: **What is happening, and when?**

It combines:

- standalone Calendar-owned events and appointments;
- source-linked dates projected from Atlas, Meridian, Education, Pets, Homestead, Travel, Solace
  and other permitted domains;
- derived birthday occurrences;
- generic rotating schedule layers;
- permission/person/source filters and multiple time views.

Calendar is a timeline and event store for Calendar-owned records. It is not the owning database for
another node's business record.

## 2. Source-of-truth rule (D7)

A date has one owner.

### Calendar-owned records

Standalone events/appointments created directly in Calendar are owned by `scheduling` and are
editable there (and through shared in-context editors such as Atlas Appointments & events).

### Node-owned records

A node record keeps its semantic date/time/recurrence. The shared scheduling helper creates,
updates or removes the corresponding `CalendarEvent` projection and preserves source linkage.

Editing a generated event directly is rejected or redirected to its owner; do not maintain a second
manual date in Calendar.

## 3. Event model and classification

A Calendar event carries the implemented combination of:

- title/description;
- start/end/all-day/timezone;
- location;
- colour/person assignment;
- visibility/sensitivity;
- recurrence where applicable;
- source node/type/id/deep-link/classification for derived records.

Standalone classification includes ordinary events and **appointments**. Derived types such as
birthdays/tasks/holidays are classifications/projections, not independent editable copies.

### 3.1 Multi-day spans (v0.41)

A `CalendarEvent` is one row regardless of how many days it covers — there is no per-day
duplication, in the database or in any API response. `end_at` is optional; when absent, the
event is a single instant (a timed event) or a single day (all-day).

**All-day inclusive end.** The date pickers (`DateTimeField`) store an all-day event's `end_at`
as **midnight of its last included day** — picking "15 Nov" as the end of an all-day event
stores `2026-11-15T00:00:00`, and 15 November is part of the event. This is the one place the
date math needs care: every reader that turns `end_at` into an *exclusive* upper bound (a range
query, a day-grid loop) must add one day to an all-day `end_at` first. `eventDayRange()`
(frontend, `src/lib/calendarSpans.ts`) and `_EFFECTIVE_END` (backend,
`apps/scheduling/selectors.py`) are the two canonical places this adjustment happens — nothing
else should re-derive it.

**Range queries must use overlap, not `start_at` membership.** `GET /calendar/events/?start=&end=`
answers "what overlaps this window", not "what starts in this window": an event starting 23
October and ending 15 November must still be returned when the window is November, because it is
still happening then. The rule, applied in `selectors.list_events`:

> the event starts before the window ends, **and**
> the event has no end, or its (exclusive, inclusive-adjusted) end is after the window start.

Querying `start_at >= window_start` alone — the bug this section exists to prevent — silently
drops every event that began before the window but is still running inside it.

**Rendering.** The frontend never asks the backend to pre-slice an event by day. It fetches the
visible window once (as before) and derives per-day/per-week placement client-side:
`eventDayRange()` turns an event into the inclusive calendar-day range it occupies;
`buildWeekSegments()` clips that to one week at a time, producing one segment per week an event
touches (flat-edged where it continues past that week, rounded where it actually starts/ends
there); `assignLanes()` packs a week's segments into deterministic, non-overlapping rows, trying
to keep a continuing event in the same lane from one week to the next. Month view renders these
segments as continuous bars (date numbers on top, lanes underneath) rather than a truncated chip
list per cell — see `MonthWeekRow` in `CalendarPage.tsx`. Week view shows the same segments as an
all-day strip above the day columns, so a spanning event is not repeated in every day column it
touches. Day view and Agenda read the same per-day index (`eventsByDay`, keyed by every day in
range, not just the start day) and show a visible date range rather than one bare time per day.

### 3.2 Presentation hierarchy (v0.41.1)

Month view mixes things of very different importance — a trip the household is taking, a bill
reminder, a school term that only describes when school is in session. Rendering all of it with
equal visual weight makes the grid read as noise rather than answering "what am I doing". Every
event is classified into one of four presentation levels, computed in
`src/lib/calendarPresentation.ts` (`presentationLevel()`) from fields the backend already
exposes — **never** by pattern-matching a title, which would be both fragile (any provider's
wording could change) and wrong (a household's own event could coincidentally use the same
words):

| Level | Meaning | Default applies to |
|---|---|---|
| `prominent` | Strongest bar, full saturation — the primary answer to "what am I doing" | Standalone HomeStack events/appointments; node-synced appointments (any node) |
| `compact` | Smaller, lighter-weight bar — still a solid colour, still tappable | Bills/purchases (Solace), reminders/tasks (Atlas/Meridian), assessments (Education), treatments/appointments metadata, maintenance (Homestead), birthdays, public holidays, generic ICS subscriptions |
| `context` | Thin, desaturated range — present but deliberately quiet | A school source's `holiday`-tagged entries (published vacation ranges) |
| `milestone` | No bar at all — a small dot + "X starts" / "X ends" marker on the two boundary days only | A school source's ranged entries that are **not** tagged `holiday` (terms) |

Classification keys off `event_kind`, `source_node`, `calendar_source_id` and the event's own
`calendar_source_kind` (the source's fixed `CalendarSource.Kind` — "school" / "holidays" /
"subscription" / "import" — exposed read-only by `CalendarEventSerializer` precisely so the
frontend never has to guess it). A school **term** and a school **break** come from the very same
provider and same `CalendarSource`; what tells them apart is `event_kind`: providers
(`apps/scheduling/sources/au_school.py`, `au_holidays.py`) tag a break or a public holiday
`event_kind: "holiday"` and leave a term at the model's own default ("event"). `sync.py`'s
`_payload()` is what threads a provider's `event_kind` choice onto the stored `CalendarEvent` —
no new field, no migration; `event_kind`'s existing "holiday" choice was simply never populated
by these providers before.

**Lane priority.** `assignLanes()` (in `calendarSpans.ts`) takes an optional per-segment
`priority` (lower claims a lane first). Month view attaches each presentation level's priority
(`prominent` < `compact` < `context` < `milestone`) before assigning lanes, so when a week is
busy, prominent household events keep the visible lanes and context/milestone entries are the
first pushed into "+N more" — a school-term marker can never displace a real event out of sight.

**Milestones.** A term is never duplicated into a second database row to get this behaviour.
`buildMilestoneMarkers()` derives up to two single-day markers (start/end) from the one
`CalendarEvent`'s existing date range, purely at render time; the stored record — and its actual
start/end dates — is untouched, and clicking either marker opens the same underlying event.

**Display-text cleanup.** `monthDisplayTitle()` strips a known, backend-authored, purely
redundant prefix — `"Bill: "`, added unconditionally by Solace for every bill
(`apps/solace/models.py`) — from Month view's compact bar label when `source_node === 'solace'`
already says the colour/position means "bill". This never touches the stored title: the event
editor, Agenda and Day view always show the full original text.

**Rotating schedules stay outside this system entirely** — they render in their own dedicated
indicator row (§8), never competing for a lane with ordinary events, exactly as before this
hierarchy was introduced.

## 4. Appointments — shipped

Calendar-owned appointments support the current useful combination of date/time/all-day state,
location, provider/contact/notes, People, visibility/colour and recurrence/reminder behavior.

They appear once in Calendar and can be projected into Atlas Agenda / Appointments & events without
creating an Atlas record.

Node-owned appointments (for example Pets and future Health) remain owned by the node and only
project into Calendar.

## 5. Views and navigation

Calendar supports responsive household views such as:

- Month;
- Week;
- Day;
- Agenda.

Required UX rules:

- Calendar is reachable from the global shell on every device;
- phone Month view remains a useful full calendar rather than collapsing into a list;
- selecting a day can reveal detail without losing month context;
- filters/person/source context remain understandable;
- date navigation handles month-end/timezone boundaries safely;
- Calendar rows deep-link to the owning record where applicable;
- a multi-day event renders as one continuous bar across the days it spans (§3.1), not as a
  separate truncated entry in every cell it touches — TimeTree's month view is the UX reference,
  translated into HomeStack's own colours/components rather than copied;
- overlapping events on the same day(s) are packed into deterministic lanes, in presentation-
  priority order (§3.2), so a real household event is never the one pushed into "+N more" by a
  lower-priority context/milestone entry;
- rotating-schedule occurrences (§8) get their own indicator row/layer in Month view rather than
  competing with ordinary events for a lane;
- context (e.g. school holidays) and milestone (e.g. school terms) entries read as quiet
  background information, never as loud as a real household event (§3.2) — a school term in
  particular shows only its start/end as small markers, never a multi-week saturated bar.

## 6. People, colour and visibility

Person/source colour makes the timeline glanceable but never replaces labels or permission logic.

Every query is permission filtered. Sensitive/financial/private events must not become visible
merely because the Calendar knows their date.

The source record's current visibility/sensitivity remains authoritative for generated events.

## 7. Recurrence (D8)

General recurrence uses the established RRULE-style `recurrence_rule` on the owning record.

Do not add parallel per-node recurrence formats. Occurrence expansion/calculation should be bounded
to requested windows and preserve ownership/security.

Whether a particular recurring domain materializes occurrence/history rows is a domain decision;
that does not change the Calendar recurrence contract.

## 8. Rotating schedules (D23) — shipped

Generic alternating two-state schedules (shared care, shift/on-call-style use) use one anchored
cycle and sparse date exceptions.

The selector calculates only the requested Calendar window. The model does **not** generate an
unbounded `CalendarEvent` row for every future day.

A changed date creates/reuses one exception; removing the exception restores the calculated plan.
The UI shows the state and exception in a way that is not colour-only.

## 9. Birthdays

Household birthdays are derived from People rather than copied into yearly event records. The
turning age is calculated for the requested year/date.

External Atlas contacts can also contribute birthday occurrences according to the Daily
Coordination contract while avoiding duplication of linked household People.

Birthdays are Calendar information rather than Atlas Agenda work.

## 10. Atlas coordination

Atlas **Agenda** is an actionable permission-filtered projection of Calendar/source-owned work.
Atlas **Appointments & events** provides browse/manage context for standalone Calendar records.

Calendar remains the source for standalone appointments/events; node records remain sources for
node-derived entries. In-context editing must call the owning API/service rather than create another
copy.

## 11. Hub

Calendar can contribute upcoming/today information to Hub through permission-aware selectors.
Hub does not own or persist the event.

## 12. Notifications

Calendar/appointment reminders use the shared Notifications/Web Push preference system. Calendar
does not maintain its own device subscriptions or push delivery service.

Sensitive event payloads remain sparse until HomeStack is opened and permissions/re-auth are
re-checked.

## 13. Kiosk

Kiosk Calendar is a simplified permission-safe timeline. It must not expose sensitive financial,
medical/private or otherwise restricted events merely because the adult web Calendar can see them.

Rotating schedules and household-safe events may be useful kiosk context where explicitly allowed.

## 14. Search / deep links

Calendar detail/source metadata can participate in navigation and Search according to permission
rules. A deep link is never authority; the destination/API re-checks the current User.

Generated event links should point back to the exact owning domain record rather than a generic
landing page where practical.

## 15. Data ownership

Exact schema/route names are defined by current Django models/migrations/URLconfs. Main Calendar
families include standalone/source-linked Calendar events and D23 rotating schedule/exception data.

Do not turn this spec into a field-by-field schema duplicate of the code.

## 16. Acceptance invariants

- Editing a node source date updates one Calendar projection without drift/duplicates.
- Clearing/deleting the source date removes the mirror appropriately.
- Editing a standalone appointment changes the Calendar-owned record, not an Atlas copy.
- A private/sensitive event is absent from unauthorised Calendar, Agenda, Hub, Search and kiosk.
- A rotating schedule can forecast a bounded future window without creating daily database rows.
- Removing a rotation exception restores the underlying repeating plan.
- Birthday ages remain correct without annual event-copy jobs.
- Phone and desktop views remain usable and deep links return to the correct source.
- A multi-day event appears on every applicable date — including a later month it merely
  overlaps, not just the one it started in — as one record, never duplicated per day.
- Clicking any week's segment of a multi-day event, in any view, opens the same underlying event;
  editing or deleting it updates/removes the whole span.
- A school term never renders as a multi-week bar; a school holiday range still renders as a
  range, but visibly quieter than a real household event (§3.2).
- A presentation-policy change (§3.2) never mutates a stored title — Month view's compact label
  may hide a redundant prefix, but the event editor, Agenda and Day view always show the full
  original text.

## 17. Future possibilities

External calendar synchronization, invitations/RSVP, richer recurrence editing and native-client
calendar integration remain future work. Any external sync must preserve HomeStack's one-source
ownership and permission model rather than create a second uncontrolled master calendar.