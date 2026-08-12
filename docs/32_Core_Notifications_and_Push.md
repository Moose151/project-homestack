# Core Spec — Notifications and Push

> Canonical. Extends and supersedes `docs/30_Core_Daily_Coordination.md` §7 ("Custom phone
> notifications") and §8 slice 4 ("Preferences and PWA foundation"), which sketched this feature
> before HTTPS existed. HTTPS on the LAN is now live (`docs/05_Security_Architecture_Document.md`
> §14), so this is buildable. Global rules apply: shared infrastructure, not a node (`apps/notifications`
> already follows this pattern — nodes call it directly, like audit/scheduling, D4); central
> permission/visibility resolution (D10); no durable event bus beyond the existing thin signal
> wrapper (D4); scheduled work is an idempotent Django management command on cron (D5).

## 1. Outcome

Every notification-worthy thing that happens in HomeStack — an appointment approaching, a to-do
due, someone adding to a shared list, a workout finished, a countdown ticking down — reaches the
right person, in the way they've chosen, without spamming them. Preferences are genuinely
granular (per category, per channel) and live in one place per user, not scattered per node.
Phone delivery is standards-based Web Push; the in-app notification centre (`apps/notifications`,
shipped) remains the source of truth regardless of whether push succeeds.

## 2. What already exists (read before building)

- **`apps/notifications`** (shipped): `Notification` model, `create_notification`/`notify_person`/
  `notify_person_id`, `mark_read`/`mark_all_read`, `GET /notifications/` + read endpoints, a bell
  UI. ~13 call sites across `achievements`, `atlas`, `education`, `fitness`, `link_imports`,
  `meridian`, `solace`, `travel` call these **directly and unconditionally** — no preference gate
  exists today. This spec adds the gate *inside* `create_notification`/`notify_person` so every
  existing call site respects preferences automatically, without each node needing to check.
- **The event bus is already wide** (`apps/events/bus.py`, D4): `publish`/`subscribe` on named
  string topics. Every major node already has an `events.py` with topics like
  `scheduling.event_created`, `atlas.list_item_completed`, `fitness.session_completed`,
  `meridian.task_approved`, `homestead.maintenance_completed`, `pets.treatment_completed`, and
  many more (~40 topics total across 11 apps). **Most are publish-only — nothing subscribes to
  them yet**, and a few (`scheduling.event_created`/`event_updated`/`event_deleted`) are defined
  but **never actually called** from `apps/scheduling/services.py` — wiring the publish call is
  part of this work, not already done. `apps/achievements`, `apps/homestead` and `apps/solace`
  already have a `handlers.py` subscribing to other nodes' events via `AppConfig.ready()` — this
  spec's dispatcher follows the exact same pattern (`apps/notifications/handlers.py`).
- **Bundling already has a working precedent.** Corner reactions
  (`apps/people/corner_services.py::_notify_reaction`) collapse a burst of reactions on one
  activity into a single evolving notification: it looks for an existing **unread** notification
  on the same `(recipient, source_node, action_url)` created within the last hour and updates its
  title/message in place, rather than creating a new row per reaction. This spec generalises that
  exact mechanism into a shared helper instead of leaving it Corners-only.
- **The Hub Countdown widget already exists** (`apps/hub`, v0.19.1): one household-wide
  `target_date`/`target_time` in `HouseholdHubWidget.settings_json`. "Daily countdown push" reads
  this existing widget — it does not need a new countdown model.
- **`Household.timezone`** already exists and is the correct source for "morning" / quiet-hours
  time-of-day math (the same field the Solace timezone fix used this session).

## 3. Notification categories

One flat, finite list — each is a real toggle in preferences, each maps to concrete event(s)/job(s):

| Category | Source | Trigger |
|---|---|---|
| `appointments` | Calendar | Appointment/event within 24h or due this morning |
| `assigned_tasks` | Atlas, node-owned due items | Assigned to-do/reminder within 24h or due this morning |
| `household_activity` | Atlas, Calendar, Homestead rooms, Travel | Someone else adds/changes a shared list, calendar entry or room plan item (**bundled**, §6) |
| `home_maintenance` | Homestead | Maintenance/pool-care due or completed, warranty expiring |
| `meridian` | Meridian | Task approved/rejected, reward approved, allowance paid, badge earned |
| `fitness` | Fitness | Someone completes a workout, a personal record is set |
| `books` | Books | Someone finishes a book, a club book changes |
| `travel` | Travel | New destination idea added, booking deadline approaching |
| `wish_price_alerts` | Link imports / Corners | A watched price drops/hits target |
| `countdown` | Hub | Daily "N days/hours to go" digest while a countdown is active |
| `corners` | Corners | Reaction, comment or help offer on your activity (already bundled, §2) |
| `account` | Accounts/Audit | Security-relevant: password/PIN changed, new device, admin action on your account |

Each category has two independent toggles (**in-app**, **push**) plus, where the source
distinguishes it, an **assigned-to-me only** vs **everyone's** switch (doc 30 §7's
"assigned-to-me versus household activity"). Sensible defaults ship enabled for everything except
`household_activity` and `wish_price_alerts`, which default push-off/in-app-on (opt-in for push,
to avoid a noisy first run).

## 4. Data model

```
apps/notifications/
  models.py: Notification (existing), + —
    NotificationPreference   — (user, category) unique; in_app_enabled, push_enabled,
                                mine_only (nullable — only meaningful for categories that support it)
    UserNotificationSettings — one row per user; quiet_start/quiet_end (nullable TimeField,
                                per-user per Q&A), morning_time (default 08:00, used for both the
                                "morning of" reminder and the countdown digest)
    PushDevice                — user, endpoint (unique), p256dh, auth, label, user_agent,
                                created_at, last_seen_at, is_active
    NotificationReminderLog   — idempotency marker: (source_node, record_type, record_id,
                                lead_kind ∈ {24h, morning_of}) unique — the scheduled command
                                checks this before sending so a re-run never double-sends
```

All four new models inherit `HouseholdBaseModel` per convention. `PushDevice`/
`UserNotificationSettings`/`NotificationPreference` are addressed to **User** (D12 — the login
holder receives notifications), matching the existing `Notification.recipient_user`.

## 5. Central preference gate

`create_notification`/`notify_person`/`notify_person_id` gain an optional `category: str`
parameter (default `""` for the ~13 existing call sites that haven't been updated yet — an empty
category always creates the in-app row, matching today's unconditional behaviour, but never
triggers push, so nothing already shipped starts pushing to a phone without an explicit category
being added deliberately). When `category` is set:

1. Look up `NotificationPreference` for `(recipient_user, category)`. Missing row = defaults from
   §3. `in_app_enabled=False` → the function returns `None`, nothing is created at all (matches
   "fully customisable" literally — off means off, not "still logged, just hidden").
2. If `push_enabled` and the user has active `PushDevice` rows and it isn't currently that user's
   quiet hours (`UserNotificationSettings`, Household-local time, §2 Q&A: **push only** — the
   in-app row above is unaffected by quiet hours), send Web Push to each device (§8).

This keeps every call site simple — nodes pass a category string, the shared layer does the rest.

## 6. Bundling burst activity — DONE (v0.34.12, `apps/notifications/services.py::notify_bundled`)

Shared helper generalising `_notify_reaction` (§2):

```python
def notify_bundled(user, *, title, message, source_node, action_url,
                    category="", window_minutes=60):
```

Looks for an existing **unread** `Notification` with the same `(recipient, source_node,
action_url)` created within `window_minutes` and updates its title/message rather than creating a
new row — exactly the Corners mechanism, moved into shared code. `action_url` already uniquely
identifies the bundled *thing* (a list, an activity) in every real call site, so the separate
`key` parameter this section originally sketched turned out to be redundant and was dropped
during implementation. `household_activity` and `corners` are the two categories that use this;
everything else (reminders, countdown, direct assigned notifications) creates a fresh row per
event, since those are inherently one-per-occurrence, not bursty. Push is only attempted on the
*first* notification of a burst — a later update within the window never re-pushes.

Window is **60 minutes** (§2 Q&A, matching the existing Corners behaviour exactly — no new
constant to tune).

## 7. Event-bus dispatcher — DONE (v0.34.12)

`apps/notifications/handlers.py`, subscribed via `NotificationsConfig.ready()` (matching
`apps.achievements`/`apps.homestead`/`apps.solace`). Each event handler re-fetches the affected
record through its own queryset and re-checks `apply_visibility` **per candidate recipient**
(never trusts the thin event payload for anything permission-relevant), then calls
`notify_bundled` under `household_activity` for every household member who can see the result,
excluding the actor.

**Wired and live** (three handlers cover the literal owner request — calendar/shopping-list/
book examples; workout completion was already covered in slice 1):
- `scheduling.event_created` — was defined but never actually called from
  `apps/scheduling/services.py::create_event`; the publish call is now wired in.
- `atlas.list_item_created` — new topic, published from `apps/atlas/services.py::create_list_item`.
  Covers every list type (grocery/shopping/todo/checklist/general/wishlist), not just shopping —
  a personal/private list's additions are excluded automatically by the visibility re-check, no
  extra category-specific filtering needed.
- `books.entry_finished` — new topic, published from `apps/books/services.py` when a
  `PersonalBookEntry` transitions **into** `history` status (not fired again on every subsequent
  save while already there).

**Deliberately left unwired** (would double-notify or wasn't part of the literal request):
`fitness.session_completed` already has its own direct `notify_*` call from slice 1
(`category="fitness"`) — subscribing it here too would send two notifications for one workout.
`atlas.list_item_completed`, `meridian.task_approved`/`rejected`, `homestead.maintenance_completed`,
`pets.treatment_completed`, `homestead.room_item_created` and club-book status changes remain
real, available extension points for this same dispatcher — add a handler + a `connect()` line
when the household actually wants that surface, following the pattern in `handlers.py`.
`travel.idea_created` keeps its existing inline notify call from before this spec (§2) rather
than being migrated — no functional reason to touch working code.

## 8. Scheduled reminders (appointments, assigned to-dos) — DONE (v0.34.13)

New idempotent management command `notifications_run_scheduled` (D5 pattern, matching
`solace_run_scheduled`/`link_imports_run_scheduled`), `apps/notifications/tasks.py::
run_due_reminders`, run hourly — it only needs to catch the two fixed lead times, not arbitrary
ones:

- **24 hours before**: for every visible Calendar appointment/event and every Atlas item with a
  due date, if `start_at` is between 23–25h away (hourly cron tolerance) and no
  `NotificationReminderLog` row exists for `(record, "24h")`, notify assignees (or the whole
  household if unassigned) under `appointments`/`assigned_tasks`, then log it.
- **Morning of**: same sweep, but firing once per user at their `morning_time`
  (`UserNotificationSettings`, default 08:00 Household-local) for anything due *that calendar
  day*, logged under lead_kind `"morning_of"`.

This is deliberately **not** the fully generic "configurable lead times" from doc 30 §7 — the
owner asked for exactly these two fixed points. The model (`NotificationReminderLog.lead_kind`)
leaves room to add more later without a redesign, but V1 ships only these two.

**Implementation notes (adjusted from the sketch above while building):**
- **Sourced from `CalendarEvent`, not two separate sweeps.** Calendar single-source-of-truth
  (D7) means every Atlas item with a `due_at` already mirrors into `CalendarEvent` via
  `CalendarSyncMixin`, so one query covers both "Calendar appointment/event" and "Atlas item
  with a due date" — no separate Atlas-model sweep needed. The category is derived from
  `CalendarEvent.source_node`: unset (a standalone event) → `appointments`/`source_node=
  "scheduling"`; `source_node.key == "atlas"` → `assigned_tasks`/`source_node="atlas"`.
- **Scope is narrower than "every visible Calendar entry."** Other synced nodes (Solace,
  Meridian, Homestead, Pets, Travel, Education) are deliberately excluded from the sweep —
  Solace already runs its own reminder job (`solace_run_scheduled`) and is re-auth-gated
  besides, and the owner's literal ask was appointments and assigned to-dos, not a generic
  reminder layer for every node. Extending the sweep to another node is a one-line change to
  `apps/notifications/tasks.py::_reminder_events`'s filter when actually wanted.
- **`NotificationReminderLog.recipient_user` was added** (not in the original four-field
  sketch) and is `null` for the 24h-before reminder — one log row locks the *event*, covering
  every recipient at once, since the lead time itself doesn't depend on any individual's clock
  — but is set per-recipient for morning-of (and the countdown digest, §9), since those fire at
  a different real-world moment for each user's own `morning_time`.
- **`mine_only` is enforced here, not inside `create_notification`.** The shared preference gate
  only understands `in_app_enabled`/`push_enabled`; the reminder sweep itself filters recipients
  down to assignees when a user's `mine_only` is set for the category, since only the caller
  knows who's actually assigned to a given record.

## 9. Daily countdown digest — DONE (v0.34.13)

Same command, `apps/notifications/tasks.py::run_countdown_digest`, checked once per user per
hour but only fires at their own `morning_time`: if the Hub Countdown widget is enabled and has
a future `target_date`, send one push/in-app notification ("3 days to go" / "14 hours to go"
inside the final day) to everyone with `countdown` enabled. Idempotency: `NotificationReminderLog`
with `record_type="HouseholdHubWidget"`, `lead_kind=f"daily:{date}"`, `recipient_user=user` so it
can never double-send the same user for the same calendar day even if the command runs twice —
and each household member gets it at their own morning time rather than everyone getting it at
once.

## 10. Web Push mechanics

- **New dependency:** `pywebpush` (VAPID-signed Web Push from Python — the standard library for
  this; no other viable option without hand-rolling ECDSA signing).
- **VAPID keys**: generated once (`vapid_gen_keys` or `pywebpush`'s helper), stored as
  `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY`/`VAPID_SUBJECT` in `.env` — never in the database or
  committed. The public key is served to the frontend to create the browser subscription.
- **Frontend**: a service worker (`public/sw.js`) handling `push` (show notification) and
  `notificationclick` (focus/open the deep link) events; a subscribe/unsubscribe flow gated
  behind an explicit user action (never auto-prompt on login — browsers penalise unsolicited
  permission prompts, and doc 30 already requires "explicit permission request initiated by the
  user"); registers the subscription via `POST /notifications/devices/`.
- **Payload safety (doc 30 §7, restated because it is a hard rule, not a suggestion):** push
  payloads are deliberately sparse — a title and a generic message, never financial/health/
  private record content. The service worker's `notificationclick` opens `action_url`, which
  re-checks the session and record permission before showing anything — the payload itself is
  never the source of truth. `solace`/`health`-sourced notifications either stay in-app-only
  (recommended — these nodes are password-re-auth-gated, and a lock-screen push bypasses that
  gate's spirit even with a sparse payload) or, if ever pushed, carry the most generic possible
  text ("Money needs attention") with no amounts/names. This spec defaults to **in-app-only** for
  anything sourced from a sensitive node; push for those categories is out of scope unless the
  owner asks for it explicitly.
- **Expiry**: a `410 Gone`/`404` from the push service on send deactivates that `PushDevice`
  (`is_active=False`) rather than retrying it forever.

## 11. API surface

```
GET/PATCH /api/v1/notifications/preferences/        — list/update all (category, in_app, push, mine_only)
GET       /api/v1/notifications/settings/            — quiet hours + morning_time (self)
PATCH     /api/v1/notifications/settings/
GET       /api/v1/notifications/devices/              — this user's registered devices
POST      /api/v1/notifications/devices/register/     — subscribe (endpoint + keys from the browser)
DELETE    /api/v1/notifications/devices/<id>/          — revoke
POST      /api/v1/notifications/devices/<id>/test/     — send one test push (doc 30 §7's "test control")
```

All self-service (a user manages their own preferences/devices/settings) — no admin override
needed for V1; a parent managing a child's login can do so from that child's own session, same as
today's profile editing.

## 12. Delivery slices

1. **Preference model + gate — DONE (v0.34.10).** `NotificationPreference`/
   `UserNotificationSettings` + migration, the `category` param on `create_notification`/
   `notify_person`, preferences API + a settings-page UI. Eight real call sites tagged with
   categories so the gate has immediate effect.
2. **Web Push infrastructure — DONE (v0.34.11).** VAPID keys (`manage.py generate_vapid_keys`),
   `PushDevice` model + register/unregister/test endpoints, service worker (`public/sw.js`),
   frontend subscribe flow (explicit user action, never auto-prompted), `pywebpush` send path
   wired into the slice-1 gate — quiet hours, per-category push toggle, sensitive-node exclusion
   (queries `HouseholdNode.requires_reauthentication` generically rather than hardcoding node
   names) and automatic device deactivation on a 404/410 response are all enforced before a send
   is attempted. A minimal `manifest.json` + `apple-mobile-web-app-capable` were added because
   iOS only allows Web Push for an installed PWA, not a plain Safari tab.
3. **Event-bus dispatcher + bundling — DONE (v0.34.12).** `apps/notifications/handlers.py`
   (wired via `NotificationsConfig.ready()`, matching the achievements/homestead/solace pattern)
   subscribes to `scheduling.event_created` (newly wired — was dead code before), the new
   `atlas.list_item_created` and `books.entry_finished` topics. `notify_bundled()` extracted
   from Corners into `apps/notifications/services.py`; Corners now calls it too instead of
   duplicating the logic. Every handler re-fetches through the record's own queryset and
   re-checks `apply_visibility` **per candidate recipient** before notifying, so a private list
   or a surprise-hidden calendar event never leaks. Push only fires on the first notification of
   a bundled burst, never on every update within the window. **Simplified from the original
   design:** dropped the separate `key` parameter sketched below — `action_url` already
   uniquely identifies the bundled thing (a list, an activity), exactly as the Corners
   implementation this generalises always did, so a second identifier was redundant. Fitness
   (`fitness.session_completed`) was deliberately **not** added to the dispatcher — it already
   notifies directly (tagged `category="fitness"` in slice 1), and subscribing it here too would
   double-notify. Home & maintenance / Meridian / Travel activity notifications beyond what
   slice 1 already covers, and Homestead room-plan additions, remain a future extension of this
   same dispatcher if wanted — not required by the original ask.
4. **Scheduled reminders + countdown digest — DONE (v0.34.13).** New `notifications_run_scheduled`
   management command (recommended hourly cron, matching the existing
   `link_imports_run_scheduled`/`solace_run_scheduled` pattern) runs `run_due_reminders()` (§8)
   and `run_countdown_digest()` (§9) in `apps/notifications/tasks.py`. New
   `NotificationReminderLog` model (migration `notifications.0004`) — see §8's implementation
   notes for how it ended up shaped slightly differently from the original four-field sketch
   (a `recipient_user` column was added for per-user idempotency on morning-of/countdown).
   Sourced entirely from `CalendarEvent` (D7 single-source-of-truth) rather than querying Atlas
   models separately, since dated Atlas records already mirror there. This closes out the
   Notifications & Push feature — all four slices are done on `feature/push-notifications`.

## 13. Acceptance criteria

- Turn a category off (in-app): nothing appears for it anywhere, including the bell. Turn push
  off for one category while leaving in-app on: the bell still gets it, no phone alert does.
- Set quiet hours 10pm–7am; trigger a push-eligible event at 11pm — no push arrives until after
  7am (or not at all, for a one-off event that isn't re-sent), but the in-app bell shows it
  immediately.
- Add five items to a shared shopping list within a minute: recipients with `household_activity`
  on get **one** notification ("X added to Groceries"), not five, and it updates in place if a
  sixth item is added 10 minutes later; a new one starts after the 60-minute window closes.
- An appointment tomorrow at 3pm: assignees get a notification ~24h before and again the morning
  of, each exactly once even if the reminder command runs multiple times in that window.
- A household Countdown at "5 days to go": everyone with `countdown` enabled gets one push that
  morning, not one per hour, and never twice for the same day.
- A private Atlas list's additions never notify anyone who couldn't already see that list; a
  Solace bill event never produces a push payload with an amount or bill name.
- Revoke a device from Settings; it stops receiving push immediately and disappears from the
  device list. A push to an expired/unsubscribed endpoint deactivates it automatically rather
  than erroring on every future send.

## 14. Deliberate exclusions

Native iOS/Android push (APNs/FCM) beyond standards-based Web Push, SMS, email delivery,
per-notification granularity beyond the category list in §3, arbitrary user-defined lead times
(only the two fixed ones in §8 ship), engagement-style notification ranking/batching heuristics,
and push for sensitive-node (Solace/Health) content beyond a generic "needs attention" text are
not part of this package.
