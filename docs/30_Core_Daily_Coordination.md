# Core Spec — Daily Coordination

> **Future coordinated feature package.** This spec joins Calendar, Atlas, Homestead, People and
> Notifications without creating duplicate records. Existing architectural rules still apply:
> source records own their dates (D7), People and Users remain distinct (D12), visibility is
> resolved centrally (D10), and scheduled work begins as an idempotent management command (D5).

## 1. Outcome

HomeStack should give each person one dependable view of what is coming up and notify them in the
way they choose. Appointments, dated to-dos and home-care work appear in both the shared Calendar
and Atlas's actionable agenda, while birthdays remain visible in Calendar and a people directory
without cluttering the agenda. Pool owners can change the generated care schedule rather than
being locked to starter defaults.

This is one package because the same dates, assignments, permissions and notification preferences
must behave consistently across all of these surfaces.

## 2. Source-of-truth and projection rules

- A record is stored once. Calendar events created directly in Calendar remain Calendar-owned;
  Atlas displays them as a permission-filtered projection. An Atlas to-do remains Atlas-owned and
  uses the scheduling helper to mirror its date into Calendar.
- Every permitted Calendar entry appears in **Atlas → Agenda** except birthdays, holidays and
  virtual rotating schedules. Financial, health, private and role-restricted entries remain hidden
  unless the viewer already has permission to see the source.
- Every Atlas reminder, to-do or checklist item with a due date automatically appears in Calendar.
  There is no second “show on Calendar” switch. Changing or clearing the due date updates/removes
  the mirror through the shared helper.
- Completing a dated item removes it from upcoming Agenda views but preserves its source history
  and past calendar context. It is not recreated or copied into an archive table.
- Projected rows always offer **Open source**. Editing a synced record routes to its owning node;
  standalone appointments can use the Calendar editor.

## 3. Appointments

Calendar quick-add gains an explicit **Appointment** type alongside a general event. Add
`event_kind` to standalone events (`event`, `appointment`; derived birthday/holiday/task kinds are
read-only classifications). An appointment supports:

- title, date, start/end time, all-day option and recurrence;
- location, provider/contact, notes and optional link;
- attending/assigned People, visibility and colour;
- one or more reminder lead times using shared notification preferences.

Appointments render normally in Calendar and once in Atlas Agenda. Atlas may filter Agenda by
person, source/type and date range, but does not own or copy the appointment. Later node-owned
appointments (for example Pets or Health) retain their node as the owner and use the same Agenda
projection.

## 4. Atlas Agenda and dated work

Add an **Agenda** tab to Atlas with Today, Upcoming and Overdue groups. It combines:

- standalone Calendar events and appointments;
- due-dated Atlas items;
- all other permitted node-derived Calendar entries.

Birthdays, public holidays and rotating care layers are intentionally excluded. This keeps Atlas
actionable while Calendar remains the complete household timeline. Rows show time/date, assignee,
source badge, completion state where applicable and a source deep link. Atlas actions may complete
Atlas-owned items in place; other source types remain read-only projections.

## 5. Birthdays and people directory

### Household members

The existing `Person.date_of_birth` is the source of truth. Profile and user-management screens
must expose the field for linked household members. Saving a user's birthday must not create a
second person/contact record. Calendar derives the annual occurrence and “Alex turns 35” label at
read time, so the displayed age always remains correct and no yearly jobs or duplicate
`CalendarEvent` rows are required.

### Other people

Add **Atlas → People & birthdays** for relatives, friends and other important people who do not
have a HomeStack account. A household-scoped `AtlasContact` (working name) stores name, full date
of birth including year, relationship, notes, visibility and an optional link to an existing
`Person`. The optional link is the deduplication rule: a linked household member uses the Person
date and does not get a second birthday.

Home Wiki may show or link this directory as household reference information, but it must not own
a second structured list. Birthday occurrences appear in Calendar and the people directory, not
Atlas Agenda. Full birth dates are personal data and obey record visibility; the derived age is
calculated only after permission filtering.

For the first implementation, full year is required and a 29 February birthday appears on 28
February in non-leap years. Make that policy explicit in the UI and tests.

## 6. Editable pool maintenance schedules

Homestead → Pool & spa gains a **Care schedule** editor for starter and custom tasks. Each task
can set:

- enabled/paused;
- friendly recurrence preset (weekly, fortnightly, monthly) or advanced RRULE;
- preferred weekday and first/next occurrence;
- assignee and reminder lead time.

Before saving, show the next few generated dates. A schedule edit changes future incomplete work
only; completed occurrences and audit history never move. Changing pool type/sanitiser may suggest
new tasks, but must not overwrite a schedule the household has customised.

The current advancing `MaintenanceTask` can support the editor initially. Before claiming durable
history, add a real maintenance-occurrence record (or reuse a shared occurrence abstraction) so
each completed/skipped scheduled visit retains its original date, duration/notes and completer.
Do not manufacture historical occurrences when a cadence changes.

## 7. Custom phone notifications

Add shared notification preferences per user, with device subscriptions beneath the user rather
than preferences duplicated in every node. Settings should offer:

- category controls: appointments/calendar, assigned to-dos, home/pool maintenance, Meridian,
  Fitness social activity, wish-price alerts and future categories;
- channel controls: in-app and phone push initially; email remains later;
- immediate or digest delivery, configurable lead times and quiet hours in Household local time;
- assigned-to-me versus household activity where the source supports it;
- a per-device list with revoke/test controls.

Phone delivery should begin as standards-based Web Push for the responsive PWA. It requires HTTPS,
a service worker, an explicit permission request initiated by the user and server-held VAPID keys.
Subscriptions can expire or rotate and must be removed on permanent delivery failure. Delivery is
best-effort: the in-app notification centre remains the source of truth.

Lock-screen payloads must be deliberately sparse (for example “You have an upcoming appointment”)
and fetch authorised detail after the app opens. Never place financial, health or private record
content in a push payload. Deep links re-check the session and record permission. Scheduled sends
start with an idempotent catch-up-safe Django management command/cron job; Redis/Celery remains
unnecessary until measured volume or reliability warrants it.

## 8. Proposed delivery slices

1. **Classification and agenda:** add appointment kind, make dated Atlas sync automatic, build
   the permission-filtered Atlas Agenda and source deep links.
2. **Birthdays:** expose `Person.date_of_birth`, add external contacts/deduplication, derive
   birthday occurrences and ages, and add People & birthdays.
3. **Pool schedule editor:** presets, weekday/next-date preview, future-only update semantics and
   preserved completion history.
4. **Preferences and PWA foundation:** preference model/UI, service worker, per-device Web Push
   subscriptions, safe payloads, quiet hours and scheduled dispatcher.

## 9. Acceptance criteria

- Change a weekly pool task to fortnightly Tuesday; its future dates move, completed history does
  not, and Calendar has one event per occurrence/source.
- Create and edit an appointment; it appears once in Calendar and once as a projection in Atlas
  Agenda with the same permissions and opens the same source record.
- Give an Atlas to-do a due date; it appears automatically in Calendar and Agenda. Clearing the
  date removes the mirror; completing it removes it from upcoming views without erasing history.
- Add a household user's full birth date in user management; Calendar shows the correct turning
  age without creating an Atlas contact. Add an external person's birthday in Atlas and see it in
  Calendar but not Agenda.
- Configure two users with different categories, lead times and quiet hours. Only eligible,
  subscribed devices receive the safe push, while both users retain the correct in-app history.
- Permission tests prove private/sensitive appointment details, birthdays and node-derived events
  do not leak through Agenda, notification text, search, kiosk or a push deep link.

## 10. Deliberate exclusions

Native mobile applications, SMS, external calendar sync, invitations/RSVP, an address-book sync,
engagement-style notification ranking and full maintenance workforce scheduling are not part of
this package.
