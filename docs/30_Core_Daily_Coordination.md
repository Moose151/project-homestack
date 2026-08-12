# Core Spec — Daily Coordination

> **Current core contract.** Appointments, Atlas Agenda, automatic dated-item Calendar sync,
> People/birthdays, editable pool schedules and the notification/PWA follow-up are shipped.
> Notification delivery mechanics are owned by `32_Core_Notifications_and_Push.md`.

## 1. Outcome

HomeStack gives each household member one dependable view of what is coming up without copying the
same fact into several databases.

Calendar is the complete timeline. Atlas Agenda is the actionable projection. People are the
source of truth for household birthdays. Homestead owns pool-care schedules. Notifications deliver
attention without taking ownership from any of those sources.

## 2. Source-of-truth rules

- Calendar-owned appointments/events remain owned by `scheduling`.
- Atlas to-dos/checklist items/reminders remain Atlas-owned; a due date automatically creates or
  updates their Calendar projection through the shared helper.
- Other node-owned dates remain owned by their node and project into Calendar through D7.
- Atlas Agenda is a permission-filtered view of permitted actionable Calendar content, not a
  second event table.
- Birthdays are derived from People/Atlas-contact data rather than annual copied event records.
- Pool-care schedule changes affect future incomplete work while preserving completion/history.
- Every projected row retains an exact source/deep-link or an explicitly safe inline action.

## 3. Calendar appointments/events

Standalone Calendar records distinguish ordinary events and appointments where that classification
is useful to UX/filtering.

An appointment can include the implemented combination of date/time/all-day state, location,
provider/contact/notes, People, visibility/colour and recurrence/reminder behaviour.

Atlas **Appointments & events** is a browse/manage projection of Calendar-owned records with
filters; it does not copy them into Atlas.

## 4. Atlas Agenda

Agenda groups permitted actionable items into useful time states such as Today, Upcoming and
Overdue.

It may combine:

- standalone Calendar events/appointments;
- due-dated Atlas work;
- permitted node-derived Calendar entries.

Birthdays, holidays and rotating background schedule layers are intentionally excluded from the
actionable Agenda where they do not represent work.

Rules:

- Atlas-owned work can expose safe completion/edit actions in place;
- Calendar-owned events can use the shared Calendar editor;
- node-owned rows either expose owner-approved actions or open the exact source;
- private/financial/health/restricted content is filtered before presentation.

## 5. Birthdays and People

### Household People

`Person.date_of_birth` is the source of truth for household members. Derived Calendar birthday
occurrences calculate the turning age at read time; no yearly `CalendarEvent` row is required.

### Other people

Atlas People & birthdays stores important non-login external contacts without creating fake
HomeStack Users. Where an external contact is linked to an existing Person, the Person remains the
birthday source to avoid duplicates.

Birthday visibility follows the underlying Person/contact permissions. Birthdays appear in the
Calendar/people views but not the actionable Atlas Agenda.

The current leap-day policy should remain explicit in code/tests/UI rather than hidden in date math.

## 6. Pool maintenance scheduling

Homestead Pool & spa owns pool-care schedule configuration.

The household can adjust enabled/paused state, cadence/recurrence, preferred timing/next occurrence,
assignee and reminder settings as supported by the implementation.

Important invariant: editing the schedule changes future incomplete work, not historical completed
care. A generated/advanced maintenance record must preserve its source/history semantics rather than
rewriting the past to match the new cadence.

## 7. Notifications handoff

The original Web Push design that lived in this document is no longer authoritative. The dedicated
notification implementation is shipped; use `32_Core_Notifications_and_Push.md` for:

- notification categories and per-user channel preferences;
- per-user quiet hours and morning time;
- per-device subscriptions;
- service-worker/PWA behaviour;
- VAPID/Web Push delivery;
- sensitive-node lock-screen protection;
- one-hour household-activity bundling;
- fixed 24h/morning-of reminders for the bounded Calendar/Atlas scope;
- Hub countdown delivery;
- subscription deactivation/failure behaviour.

This coordination spec defines what a reminder/activity is *about* and which source record owns the
underlying fact. Notifications never become the source of truth for the event/task/birthday/pool
schedule itself.

## 8. Acceptance invariants

- Create/edit a Calendar appointment: it appears once in Calendar and once as a projection in Atlas
  where appropriate, with matching permissions.
- Add/change/clear an Atlas due date: Calendar projection creates/updates/removes without a second
  manually maintained date.
- Completing dated work removes it from upcoming actionable views without erasing historical/source
  state.
- Household birthday age is derived correctly from the Person date and does not create a duplicate
  contact/event store.
- External birthday contacts remain separate from login Users and deduplicate correctly when linked
  to a Person.
- Changing a pool schedule does not rewrite completed history.
- Private/sensitive records do not leak through Agenda, Calendar labels, Search, kiosk or
  notifications.
- Notification delivery remains optional/best-effort and does not make the owning write depend on
  a phone/browser push service.

## 9. Current status

The coordination/data-projection slices and their PWA/Web Push delivery follow-up are shipped.
Remaining work here is ordinary live validation/bug fixing rather than a separate active
coordination milestone.

Future native mobile apps, SMS, external calendar sync, invitation/RSVP systems and address-book
sync remain outside this core coordination contract.