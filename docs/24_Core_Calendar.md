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
- Calendar rows deep-link to the owning record where applicable.

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

## 17. Future possibilities

External calendar synchronization, invitations/RSVP, richer recurrence editing and native-client
calendar integration remain future work. Any external sync must preserve HomeStack's one-source
ownership and permission model rather than create a second uncontrolled master calendar.