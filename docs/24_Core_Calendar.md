# Core Spec — Calendar

> Canonical. **Core service, not an opt-in node.** Ships in every install and cannot be
> disabled. The Django app is named **`scheduling`**, never `calendar` (D16 — avoids the stdlib
> clash). Global rules from `00_README_and_Changelog.md` apply: `CalendarEvent` inherits
> `HouseholdBaseModel`; the calendar is the **one source of truth for dates (D7)** — node records
> own their dates and call the scheduling helper, which creates/updates/deletes
> `calendar_events` and writes `calendar_event_id` back; **nodes never write calendar rows
> directly**; one recurrence format `recurrence_rule` (RRULE, D8); `created_by/updated_by` =
> user, `assigned_to_person` = person (D12); central resolver + visibility mixin (D10).

## 1. Purpose

The Calendar is HomeStack's shared household timeline — the single place every dated thing
appears, no matter which node created it: Atlas reminders, Meridian deadlines, Pets vet
appointments, Education school events, Travel bookings, Home Wiki review dates, and standalone
events the family adds directly. It answers ***"What's happening, and when?"*** across the whole
household in one consistent, permission-aware view.

It must be **accessible from every page**, **easily configurable**, and **nice to look at** —
those are first-class requirements, not polish (see §14–§16).

## 2. Philosophy

**One source of truth for dates (D7).** A date is owned by exactly one record. Node records own
their own dates and mirror them into `calendar_events` *only* through the scheduling helper
(`sync_event_for` / `delete_event_for`), which writes `calendar_event_id` back. The Calendar
never holds a second, hand-maintained copy of a node's schedule, and nodes never write calendar
rows. The result: edit a reminder in Atlas and the calendar updates itself; nothing drifts.

The Calendar is a **timeline + event store**, not a node and not the Hub. The Hub shows "what
needs attention today" (a curated slice); the Calendar shows the full chronological picture.

## 3. What belongs in the Calendar

Every dated household item: standalone events (appointments, birthdays, "people coming over"),
and **node-derived events** synced in from their source records — Atlas dated reminders/to-dos,
Meridian deadlines, Pets treatments/vet visits, Education assessments/school events, Travel
bookings, Home Wiki review reminders, Solace bill due-dates (sensitivity-gated). All-day and
timed events; recurring events via `recurrence_rule`.

## 4. What does NOT belong in the Calendar

A node's full domain record (the calendar mirrors only its date/title/visibility, not the whole
thing). A second copy of a node's schedule. Tasks with no date (those live in their node). The
"today" curation (Hub). The notification log (Notifications). The Calendar shows time; it does
not own node business logic.

## 5. Primary users

Admins, managers, users, permitted child accounts, kiosk users. Children/kiosk see a simplified,
permission-filtered timeline — only household and permitted events, never sensitive ones.

## 6. Key features

**Events (`CalendarEvent`)** — `title`, `description`, `start_at`, `end_at` (nullable),
`is_all_day`, `timezone`, `recurrence_rule`, `assigned_to_person`, `colour`, `location`,
`visibility`, `sensitivity`, plus the source link (`source_node`, `source_record_type`,
`source_record_id`) set when the event mirrors a node record. `is_synced` = "owned by a node
record"; `is_synced` events are **read-only via the API** (edit the source record instead).

**Standalone events** — created directly via the API (`POST /calendar/events/`); fully editable
in place.

**Node-derived events** — created/updated/deleted automatically by `sync_event_for(record)` when
a node record with a date changes; removed by `delete_event_for(record)` / when the source date
is cleared. The node owns the truth; the calendar reflects it.

**Recurrence (D8)** — one format, `recurrence_rule` (RRULE), stored on the owning record and
copied onto the event for display. *Full RRULE expansion into occurrences is deferred* — V1
stores and displays the rule; the renderer expands a window when expansion lands.

**Colour & assignment** — per-event `colour` and `assigned_to_person` drive a clear, glanceable,
per-person colour-coded timeline ("nice to look at", §16).

## 7. Permissions

Resource: `scheduling` (`scheduling.view/create/edit/delete`). Every event carries `visibility`
(private · household · role_restricted · sensitive) and `sensitivity` (normal · financial ·
health · document · private). All reads run through the central resolver + visibility mixin
(D10) — children never see sensitive/financial/health events; private events show only to their
owner; node-derived events inherit the source record's visibility/sensitivity via the helper.
Synced events reject direct API writes (edit the source). No ad-hoc checks in views.

## 8. Node integration (how dates flow in)

A node with dated records: (1) makes the record carry `calendar_event_id` + implement
`get_calendar_data()` / `get_calendar_node_key()`; (2) calls `sync_event_for(self)` on save and
`delete_event_for(self)` on delete (via `CalendarSyncMixin`). The helper does the rest —
create/update/delete the event, copy visibility/sensitivity/colour/recurrence, write the FK back.
The Calendar **never imports node models** (D4); nodes **never** touch `CalendarEvent` directly
(D7). Disable a node → its events stop syncing.

## 9. Hub integration

The Hub reads an "upcoming events" slice from the Calendar (next N permitted events) for its
widget. The Hub never writes events. The Calendar is the full view that widget links into.

## 10. Notifications

Optional, sparing: event reminder (lead time), event starting soon, event changed/cancelled,
assigned to an event. Channels via the shared Notifications service; the Calendar emits, it does
not store the notification.

## 11. Events (signals)

Publishes (future, D4): `calendar_event_created/updated/deleted`. Primarily a **consumer** of
node sync calls via the helper rather than the bus. No durable event-bus table (D4); no
Celery/Redis for reminders yet (D5) — reminder dispatch runs via the cron management command
until it outgrows it.

## 12. Search

Event title/description/location searchable via global FTS (`search`, D9), permission-filtered —
sensitive events never surface to children/unpermitted users.

## 13. Attachments

The Calendar stores no files. An event may reference its source node record, which holds any
attachments via the shared service.

## 14. Accessibility — available from every page (owner requirement)

The Calendar is reachable from **every screen**, not just a nav destination:
- A persistent entry point in the global shell (web sidebar/bottom-nav + a quick "jump to
  calendar" affordance) on every authenticated page.
- A lightweight **peek/mini-calendar** (e.g. month strip or "next up" popover) openable from any
  page without a full navigation, for a quick glance and quick-add.
- Deep-linkable: dated items across nodes link straight to their event/day in the Calendar.
- Present on web, mobile layout, and the kiosk Hub (kiosk-safe events only).

## 15. Configurability (owner requirement)

Easily configured per household and per user:
- **Views:** month / week / day / agenda(list), with a saved default.
- **Filters:** by node/source, by person (`assigned_to_person`), by visibility — toggle layers
  on/off (e.g. hide Meridian, show only "my" events).
- **Per-person colour coding** and per-event `colour`; legend always visible.
- **Start-of-week, time format, default view, default filters** as user settings (stored like
  other prefs); household-level defaults an admin can set.
- All configuration is permission-aware — a child's options never expose sensitive layers.

## 16. Look & feel (owner requirement)

"Nice to look at" is a requirement: follows the shared warm HomeStack design system, dark-mode
aware, clean month/week grids, readable typography, generous touch targets, smooth view
transitions, colour-coded per person/node, clear today marker, empty-states that feel calm not
blank. Kiosk view uses large cards and minimal chrome. Mobile view is finger-first (swipe between
periods, tap a day for its agenda).

## 17. Progressive detail

Basic: see the timeline, add a standalone event, see node events appear automatically. Standard:
month/week/day/agenda views, per-person colour, filters, all-day + timed events, assign a person.
Detailed: recurrence (RRULE expansion), saved view/filter prefs, peek mini-calendar everywhere,
reminders/lead times, household default config, drag-to-reschedule (parked).

## 18. Data model

`calendar_events` (`CalendarEvent`, inherits `HouseholdBaseModel`): `title`, `description`,
`start_at`, `end_at?`, `is_all_day`, `timezone`, `recurrence_rule`, `source_node?`,
`source_record_type`, `source_record_id`, `assigned_to_person?`, `colour`, `location`,
`visibility`, `sensitivity`; `is_synced` property; `objects = HouseholdManager`,
`all_objects = AllObjectsManager`. Owning node records carry `calendar_event_id` (FK back) and
`recurrence_rule` (the single source for recurrence, D8). Shared services: permissions resolver,
notifications, search, audit.

## 19. API

`GET /api/v1/calendar/events/` — list (permission-filtered; query by date window / source /
person as those filters land).
`POST /api/v1/calendar/events/` — create a **standalone** event (synced events are created by the
helper, not here).
`GET /api/v1/calendar/events/{id}/` · `PATCH …` · `DELETE …` — standalone events only; synced
events reject direct writes (D7) — edit the source record.

## 20. V1 scope

`CalendarEvent` store · standalone event CRUD · node-derived sync via the helper (Atlas live;
other nodes as they land) · visibility/sensitivity through the resolver · recurrence stored as
RRULE (expansion deferred) · per-person colour/assignment · web month/week/day/agenda views ·
filters · global accessibility (every-page entry + peek) · kiosk-safe timeline · user view/filter
prefs. **Not in V1:** full RRULE expansion engine, drag-to-reschedule, external calendar sync
(ICS/CalDAV — Parking Lot), invitations/RSVP, free/busy.

## 21. Risks & mitigation

Risk: dates drifting between a node and the calendar; sensitive events leaking to kiosk/children;
the calendar becoming a second store of node logic; recurrence complexity. Mitigation: **one
source of truth (D7)** — the helper is the only write path for node events, synced events are
read-only via the API; resolver/visibility on every read; the calendar mirrors only date +
display fields, never node business logic; one recurrence format (D8) with expansion deferred
until needed.

## 22. Completion criteria

The family sees one shared timeline of all permitted dated items; standalone events are
created/edited/deleted; node reminders/events appear and update automatically via the helper with
no double-writing; events are permission- and sensitivity-filtered (no leaks to children); the
Calendar is reachable from every page and offers a quick peek + quick-add; views (month/week/day/
agenda), per-person colour and filters work and are configurable; it follows the shared design
system and looks good on web, mobile and kiosk.
</content>
