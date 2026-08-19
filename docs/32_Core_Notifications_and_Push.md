# Core Spec — Notifications and Push

> **Status: shipped (v0.34.10–v0.34.13).** This is the canonical current contract for HomeStack's
> in-app notifications, notification preferences, PWA/Web Push delivery, household-activity
> bundling and scheduled reminder/countdown delivery.
>
> Notifications are **shared infrastructure, not a node**. Nodes may call the shared notification
> service directly, like audit/scheduling. D4 still applies to decoupled cross-domain reactions;
> there is no durable event broker. Scheduled work remains an idempotent Django management command
> run by host/cron scheduling (D5).

## 1. Outcome

HomeStack has one notification system with the in-app notification centre as the durable user-facing
source of truth. Web Push is an optional delivery channel layered on top of that system.

The implementation provides:

- per-user notification category/channel preferences;
- per-user quiet hours and morning time;
- multiple Web Push devices per User;
- VAPID-based Web Push delivery;
- a PWA/service worker for phone/background delivery;
- sensitive-node protection for lock-screen push;
- one-hour bundling for selected household activity;
- scheduled 24h and morning-of reminders for the deliberately bounded Calendar/Atlas scope;
- a daily Hub countdown digest;
- best-effort delivery that never makes the owning domain write depend on a push provider.

## 2. Source of truth and ownership

`Notification` is addressed to a **User**, not a Person. Nodes that start from a Person use
`notify_person`/`notify_person_id`, which resolve the linked User and no-op if none exists.

Important ownership rules:

- the in-app `Notification` row is the durable notification record;
- Web Push delivery is best-effort and may fail without rolling back the owning write;
- a push subscription belongs to one authenticated User;
- preference/settings/device endpoints operate on the current User, not arbitrary User IDs;
- notification deep links never grant access: the destination re-runs normal authentication,
  visibility, permission and sensitive re-authentication checks.

## 3. Data model

Current durable models in `apps/notifications/models.py`:

### `Notification`

- `recipient_user`
- `title`
- `message`
- `level`
- `source_node`
- `action_url`
- `is_read`
- normal `HouseholdBaseModel` ownership/audit fields

### `NotificationPreference`

Unique per `(user, category)`:

- `in_app_enabled`
- `push_enabled`
- `mine_only`

A missing preference row uses category defaults.

### `UserNotificationSettings`

One row per User:

- `quiet_start`
- `quiet_end`
- `morning_time` (default 08:00)

Times are interpreted in `Household.timezone`.

### `PushDevice`

One Web Push subscription/device/browser:

- `user`
- unique subscription `endpoint`
- `p256dh`
- `auth`
- `label` — the friendly display name
- `label_is_custom` — the owner renamed it
- `browser` / `platform` — derived secondary technical detail
- `user_agent`
- `last_seen_at`
- `is_active`

Multiple devices per User are normal.

#### Device naming

A device is named **server-side at registration** from the request's User-Agent
(`apps/notifications/device_naming.py`), producing names like `Chrome on Android`,
`Safari on iPhone` or `Firefox on Linux`. The client does not supply a label, so every client
that registers a subscription names devices identically (D3).

The parser is a deliberately small heuristic, not a User-Agent database, and does not claim
detail the User-Agent does not carry — a Firefox-on-Fedora string only says `Linux`. Where both
halves are unknown the label falls back to `New device`, never blank.

The owner may rename a device to anything (`Nick's Laptop`, `Kitchen Tablet`), which sets
`label_is_custom`. Re-registering the same endpoint refreshes keys/`browser`/`platform` but must
**not** overwrite a custom label. Renaming to blank deliberately restores the generated name.
`browser`/`platform` remain available as secondary detail shown under the friendly name, so a
renamed device is still identifiable.

### `NotificationReminderLog`

Idempotency marker for scheduled reminders/digests. It records source/type/id, lead kind and, where
needed, the recipient User so reruns/overlapping hourly jobs do not double-send.

## 4. Notification categories

The fixed taxonomy is:

| Category | Purpose |
|---|---|
| `appointments` | Calendar appointments/events, including someone adding one |
| `assigned_tasks` | Atlas/assigned due items |
| `household_activity` | Shared household changes/activity |
| `home_maintenance` | Homestead maintenance-related notifications |
| `meridian` | Meridian tasks/rewards/points workflows |
| `fitness` | Fitness activity |
| `books` | Books activity |
| `travel` | Travel activity |
| `wish_price_alerts` | Link/watch/wish price alerts |
| `countdown` | Hub countdown digest |
| `corners` | Corner reactions/activity |
| `account` | Account/security changes |

`appointments` and `assigned_tasks` support the meaningful `mine_only` preference.

Default push is **off** for `household_activity` and `wish_price_alerts`; other categories default
to push on when no explicit preference exists.

### Compatibility rule for older call sites

`create_notification(..., category="")` deliberately bypasses category preferences and preserves
preference-era in-app behaviour. It creates the in-app row and does **not** attempt Web Push.

A node/call site must opt into a real category before its notification participates in preference
filtering/push delivery. Do not silently reinterpret unclassified legacy notifications.

## 5. In-app creation and preferences

`create_notification`:

1. resolves the recipient User;
2. checks `in_app_enabled` when a category is supplied;
3. creates the in-app `Notification` row;
4. attempts Web Push for a categorized notification.

`notify_person` and `notify_person_id` are the Person-to-User helpers.

Preferences are centralized inside Notifications rather than requiring each node to query preference
models itself.

## 6. Web Push delivery

Implementation lives in `apps/notifications/push.py` using `pywebpush`.

Required deployment settings:

```text
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
VAPID_SUBJECT=
```

Generate a key pair with:

```bash
docker exec homestack-backend python manage.py generate_vapid_keys
```

The private key is a deployment secret and must never be committed or exposed to the browser.

### Delivery gates

Normal push delivery is skipped when any of these is true:

- VAPID is not configured;
- the source node currently requires sensitive re-authentication;
- the User's category `push_enabled` setting is off;
- the User is inside configured quiet hours;
- the User has no active push devices.

A test push is an explicit User action and bypasses category/quiet-hour checks, but still requires
valid VAPID configuration.

### Sensitive-node rule

`push.py` checks the current `HouseholdNode.requires_reauthentication` flag. A re-auth-gated source
is automatically in-app-only even if a future caller accidentally assigns it a push-enabled
category. This prevents Solace/Health-style protected data from being exposed on a lock screen.

### Failure behaviour

Push is best-effort. Exceptions are logged and do not propagate into the owning domain write.
HTTP 404/410 Web Push responses deactivate the affected `PushDevice`.

## 7. API contract

Current registered routes under `/api/v1/notifications/`:

```text
GET  /                         notification list
POST /read-all/                mark all read
POST /<notification_id>/read/  mark one read
GET/PUT/PATCH as implemented /preferences/
GET/PUT/PATCH as implemented /settings/
GET  /vapid-public-key/
GET/POST /devices/
POST /devices/current/
PATCH/DELETE /devices/<device_id>/
POST /devices/<device_id>/test/
GET  /household-devices/
```

The exact allowed methods/response shapes are defined by the current views/serializers/tests. The
registered paths are authoritative in `backend/apps/notifications/urls.py`.

`PATCH /devices/<device_id>/` renames a device and accepts only `label`.

`POST /devices/current/` accepts the browser's existing subscription endpoint and returns only
its matching active `device_id` (or `null`) for the current User. This lets the phone UI label and
prioritize **This phone** without ever serializing subscription endpoints into device lists.

A User cannot manage another User's device subscription by guessing its ID; detail operations are
current-User scoped. `/devices/` itself lists only the requesting User's devices — this is not an
administrator carve-out, it is the same for every role.

Device responses never include `endpoint`, `p256dh` or `auth` (§13).

### Household push-device overview

`GET /household-devices/` is the **only** cross-User device endpoint. It is:

- gated on the `users` resource, which only the admin role is granted, so it is administrator-only;
- **read-only** — an owner still tests/renames/revokes their own devices from their own
  notification settings, and no login may act on another person's device;
- grouped by owning User, active devices only, and subject to the same secret-omission rule above.

It exists for the operational question "who is actually set up for push, on what, and is that
tablet still in use". It is not a route to managing another person's notifications, and the
ordinary self-service notification screen deliberately continues to show only the current User.

## 8. Household-activity bundling

`notify_bundled` generalizes the existing Corners pattern.

For the same `(recipient, source_node, action_url)` within a one-hour window:

- if an unread notification already exists, its title/message are updated;
- no second push is sent for that burst;
- otherwise a new notification is created and normal push delivery is attempted.

This avoids a household member receiving repeated phone buzzes while someone performs a burst of
related edits.

Current event-driven household activity handlers include:

- Calendar event created — classified as `appointments`, not `household_activity`, so it
  pushes by default (see below);
- Atlas list item created;
- Books personal entry finished.

Handlers re-fetch the actual record and run permission/visibility checks for each candidate
recipient. They never trust the event payload as an authorization decision.

### Why a calendar addition is not `household_activity`

Something landing on the shared household calendar is an appointment, and `appointments` is the
category this taxonomy already describes as "Calendar appointments/events". It was originally
dispatched as `household_activity`, whose default is push **off** — so a household that believed
it had everything switched on still got only a silent in-app row when a partner added a dentist
appointment. Adding an item to a shopping list stays `household_activity`, where the quieter
default is the right call.

Bundling still applies: several events added for the same day within an hour update one
notification and buzz a phone once.

## 9. Scheduled reminders

Scheduled delivery is deliberately **not** a fully generic configurable lead-time engine.

Current `run_due_reminders` scope is limited to:

- standalone Calendar-owned events; and
- Atlas-sourced Calendar events.

Other domains that have their own reminder behaviour are not swept automatically, which avoids
unrequested duplicates.

### Wording is derived from the entry, never hardcoded

A bill, task or deadline is *due*, so it can read "Due today" and it can be "Overdue". An
appointment or event is not due — it simply happens — and a reminder reads as a reminder.
`apps/notifications/wording.py` is the single formatter for these titles, so the in-app list, the
notification bell and the Web Push payload (which all render `Notification.title`) cannot drift
apart. Classification is by `event_kind == "task"`, or `source_record_type == "AtlasReminder"`,
falling back to event/appointment.

| Entry | 24-hour lead | Morning-of lead | At its scheduled time |
| --- | --- | --- | --- |
| Task / bill / deadline | Due tomorrow | Due today | Due now |
| Appointment / event | Tomorrow | Starts at 3:30 PM (or "Today" if all-day) | Starting now |
| Reminder | Reminder tomorrow | Reminder today | Reminder |

An event or appointment must never be labelled "Due" or "Overdue".

### 24-hour reminder

The hourly job looks for relevant events in a 23–25 hour window and sends a single idempotent
notification to eligible visible recipients, worded per the table above.

### Morning-of reminder

For events due on the household-local current day, each eligible User receives a notification
when the hourly run reaches that User's configured `morning_time` hour.

### Scheduled-time reminder

Atlas reminders — and only Atlas reminders — also fire at the moment they are set for: the owner
picked an exact time expecting to hear about it *then*. Sweeping every appointment here would
notify people at the instant a meeting starts, which nobody asked for. All-day reminders are
excluded (the morning-of lead already covers them), delivery is idempotent via
`NotificationReminderLog`, and the lookback matches the hourly cadence so a reminder whose time
slipped past by more than one sweep is not resurrected. `notifications_enabled=False` on the
reminder suppresses every lead, and these notifications deep-link to the reminder itself.

`mine_only` is applied to the appropriate categories when deciding recipients. A reminder with
explicit recipients notifies only those people.

### To-do notification offsets (D19 §F, v0.40)

Atlas To-dos (`AtlasListItem` inside a `list_type='todo'` list) carry their own
`notify_offsets` — a list of minutes-before-`due_at` (0 = at time), chosen from a curated menu
(at time / 15 / 30 min / 1 / 2 hours / 1 / 2 days / 1 week before). `run_due_todo_offsets` is an
**additive** function alongside `run_due_reminders` (same command, same
`NotificationReminderLog` idempotency ledger, same `create_notification`/push delivery path) — it
is not a second independent scheduler, and it does not change the three leads above. Unlike those
three fixed leads, it loops per-item over that item's own configured offsets rather than one
hardcoded window; this is still scoped to Atlas To-dos specifically, not a fully generic
lead-time engine available to every domain (see §16).

## 10. Hub countdown digest

The existing enabled Hub `countdown` widget remains the source of truth. There is no new countdown
model.

At each User's configured `morning_time`, the scheduled job may send one daily `countdown`
notification while the target remains in the future. The job uses `NotificationReminderLog` to
prevent same-day duplicates.

## 11. Scheduled command

Run at least hourly:

```bash
docker exec homestack-backend python manage.py notifications_run_scheduled
```

The command runs both:

- due reminders (`24h`, `morning_of`); and
- the daily countdown digest.

The implementation is idempotent, so overlapping/retried hourly executions should not double-send
already claimed reminder/digest work.

## 12. PWA / device behaviour

The frontend includes the service-worker/PWA path required for Web Push.

Important deployment/acceptance rules:

- test from the production frontend build as part of production-serving work;
- browser notification permission should be requested through an intentional User flow, not an
  unexplained first-load prompt;
- each browser/device has its own `PushDevice` subscription;
- removing/revoking a device does not delete in-app notification history;
- on iOS, Web Push requires HomeStack to be installed to the **Home Screen**; an ordinary Safari
  tab is not sufficient.

## 13. Security requirements

- Never expose `VAPID_PRIVATE_KEY` through API/UI/logs.
- Do not put protected financial/medical/private detail into Web Push payloads.
- Do not treat push ownership or a deep link as authorization.
- Apply source visibility before generating event-driven notifications.
- Respect household/User ownership for preference/device APIs.
- Keep the browser's push endpoint/keys as notification infrastructure data, not public profile
  information — they are never serialized, including in the admin overview.
- Keep cross-User device visibility read-only and admin-gated; self-service device actions stay
  current-User scoped.
- Public remote access remains separately gated by the Security Architecture; Web Push and trusted
  LAN HTTPS do not make HomeStack internet-ready.

## 14. Deployment requirements

The notification implementation adds backend dependency/migration work. On the live server:

```bash
docker compose build homestack-backend homestack-frontend
docker compose up -d
docker exec homestack-backend python manage.py migrate
```

Current notification migrations after the original notification model are:

```text
0002_notificationpreference_usernotificationsettings_and_more
0003_pushdevice
0004_notificationreminderlog
0005_pushdevice_browser_pushdevice_label_is_custom_and_more
```

`0005` also backfills `browser`/`platform` and regenerates any label still carrying one of the
old client-side names (`This device`, `Android device`, …), so devices registered before
server-side naming pick up proper names on migrate without re-registering.

Then configure VAPID, recreate/restart the backend as required, register devices, run the scheduled
command and complete real-device validation.

## 15. Acceptance / live validation

Before calling the live rollout fully verified:

1. configure VAPID and confirm the public-key endpoint is available;
2. register at least two household users/devices;
3. give them different category/push/quiet-hour preferences;
4. send a device test push;
5. verify categorized normal push delivery while HomeStack is closed;
6. verify a push-suppressed category remains in-app as configured;
7. verify quiet hours suppress normal push;
8. verify a re-auth-gated source cannot send protected lock-screen content;
9. verify household activity bundles instead of buzzing repeatedly;
10. verify hourly scheduled 24h/morning/countdown delivery does not double-send on rerun;
11. tap a notification and verify current permissions are checked at the destination;
12. validate an installed Home Screen PWA on iOS if iOS is a target device.

## 16. Explicitly out of scope

Do not infer these features from the existence of Web Push:

- generic configurable reminder lead-time rules for every domain;
- email/SMS notification delivery;
- a durable message/event broker;
- Redis/Celery solely for push;
- a native APNs/FCM client architecture;
- public internet exposure;
- guaranteed push delivery as a transactional dependency.

If future workload/reliability requirements justify a background queue, change D5 deliberately
rather than introducing one incidentally.

## 17. Current completion state

The implementation branch was merged to `main` on 2026-08-12 after all planned notification slices
were completed. Its final local validation reported **875 backend tests green** and a clean frontend
TypeScript check.

The remaining work is operational rollout/validation on the real home server plus later production
serving/reliability work. Feature chronology belongs in `VERSION_HISTORY.md`; current deployment
commands and priorities belong in `HANDOVER.md`.
