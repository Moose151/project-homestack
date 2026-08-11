# Document 7 — Development Roadmap

> Canonical. Supersedes all earlier roadmap versions. Tuned for a solo developer building for
> one household on an always-on home server. Decisions D1–D23 in `00_README_and_Changelog.md`.

## Guiding principle

Build **vertically, not horizontally**. The biggest risk for a solo project this broad is
spreading a little effort across every node and never finishing one usable path. So the first
milestone is a complete, daily-usable vertical slice; every milestone after it adds one node
end-to-end. The "sell it later" ambition disciplines which decisions are permanent — it does
not add scope.

Each milestone has an explicit **Done when** so you can tell when to move on.

---

## Milestone 0 — Planning (complete)

This documentation set, the node-model decision, and the architectural decisions (D1–D18).

**Done when:** docs are consolidated to one source of truth (this set) and the old `.docx`
files are archived.

---

## Milestone 1 — Foundation / Walking skeleton (D18)

The single most important milestone. A thin but complete vertical slice you actually use.

Build:
- Docker Compose: `backend` (Django/DRF), `frontend` (React/TS/Vite/Tailwind), `postgres`.
  *(No Redis/Celery yet — D5.)*
- `HouseholdBaseModel` + household-scoped default manager + soft delete (D1).
- Seed the single household row.
- Session-based auth: avatar + PIN, plus admin/manager passwords (Argon2id) (D6).
- Users + People, with the user/person rule wired in (D12).
- The **central permission resolver + visibility queryset mixin**, with permission tests
  written first (D10).
- Settings shell and audit logging.
- **Backups with a working, documented restore** (D17).
- **Atlas** as the one real node (notes, lists, list items, simple reminders).
- **Hub + Calendar** (`scheduling`) with the shared event-generation helper (D7), so Atlas
  reminders appear on the calendar without double-writing dates.
- Kiosk shell: ambient → avatar → PIN → dashboard → timeout.

**Done when:** the family can log in (web and kiosk), use Atlas lists/reminders, see them on
the Hub and Calendar, permissions are enforced and tested, and you can back up and *restore*
the database. You use it daily.

---

## Milestone 2 — Native Meridian (D13, D14)

The highest-joy early win: it's already built, already used, kid-facing, and the heart of the
kiosk. No sensitive data, so it doesn't need the security maturation first.

Build:
- Native Meridian node on shared Users/People, scheduling, permissions, Hub widgets, kiosk UI.
- Reuse the proven reward/points/approval logic; rebuild only the shell.
- One-time import of the household's live Meridian data.

**Done when:** Meridian runs entirely inside HomeStack — tasks, points, rewards, approvals,
kid kiosk cards and celebrations — and the standalone Meridian app is no longer needed at home.

### Milestone 2 revisit — Meridian parity and adult cockpit (owner request, 2026-07-10)

After live use, the Meridian integration was judged too thin/clunky despite the earlier full-port
checkoff. Product direction: **HomeStack is the Meridian source of truth and the adult/admin
cockpit** (approvals, task/reward setup, monitoring, reports, settings), while the native
Meridian app at `/home/instructor/Documents/new/project-meridian` remains the behaviour/style
reference and may remain/adapt as the child-facing client.

Build:
- Behaviour parity first, starting with native-style task completion history: per-person
  submissions, shared/household completion rules, recurring-cycle re-arm, evidence placeholder,
  review notes, approval/rejection history, and admin complete-for-person.
- Adult cockpit UI in HomeStack: overview approvals queue, task/reward management, stock and
  setup, monitoring, points/reports, and settings. Keep it HomeStack-consistent rather than a
  jarring clone of the child-facing native app.
- Defer deeper kid-facing delight work until the source-of-truth/adult workflows are solid.

**Done when:** an adult can manage day-to-day Meridian from HomeStack without needing the legacy
admin screens: approve/reject submissions and purchases, create/edit/archive tasks and rewards,
monitor balances/activity/history, and trust the completion/ledger behaviour to match native
Meridian rules.

---

## Milestone 2.5 — Core surfaces: Hub, Atlas, Calendar (owner request, 2026-06-25)

Inserted before M3 at the owner's request. With Meridian done, the daily-use core surfaces —
the **Hub**, **Atlas**, and the **Calendar** — need to actually function and feel good before
we add more nodes on top of them. These are the screens the family touches most; getting them
right makes every later node land better. Specs: `23_Core_Hub.md`, `11_Node_Atlas.md`,
`24_Core_Calendar.md`.

Build, three workstreams:

**A. Hub — functionality & usability.**
- Per-household widget config (enable/disable, order, size) and per-user overrides (hide/
  reorder), with endpoints (the config API is currently unbuilt) and a clean web UI.
- **Establish the "every node ships its Hub widget" pattern** — a node is not done until it
  contributes its Hub widget(s) via a seeded `HubWidget` row + a permission-filtered selector
  (no cross-imports, D4). Backfill the **Meridian Hub widget** (today's tasks / points summary,
  kiosk-safe) now, and add this requirement to every node's completion criteria going forward.
- Wire the Calendar "upcoming events" widget once Calendar views land (workstream C).
- Keep it permission- and kiosk-filtered; calm, glanceable defaults. (Ambient widgets —
  clock/photo/greeting — optional low-effort nicety; **weather** stays parked, D5.)

**B. Atlas — improve functionality & usability.**
- Gap pass against `11_Node_Atlas.md`: tighten lists/items/checklists/reminders UX on web and
  kiosk, quick-add/quick-capture, grocery/shopping mode polish, due-dates and person assignment,
  clearer visual states.
- Replace the SQLite-safe `icontains` search with Postgres FTS (D9) in Atlas selectors.
- Make dated Atlas items render properly on the new Calendar (they already sync via the helper).

**C. Calendar — build the core.**
- Build the real Calendar UI beyond today's "upcoming list": month / week / day / agenda views,
  per-person colour coding, and filters (by node/source, person, visibility).
- **Accessible from every page** (persistent entry point + a lightweight peek/mini-calendar +
  quick-add), **easily configurable** (saved default view, filters, start-of-week/time-format
  as prefs), and **nice to look at** (shared design system, dark-mode, kiosk-safe view).
- Standalone event CRUD UI; node-derived events continue to flow only through the scheduling
  helper (D7). RRULE expansion may be tackled here or deferred per `24_Core_Calendar.md` (D8).
- **Completed v0.20.0:** generic rotating Calendar layers (D23) calculate an anchored two-state
  cycle without daily events, associate People once, forecast any requested window and support
  sparse one-day swaps/restores in responsive month/week/day/agenda views.

**Done when:** the Hub shows the right per-user "today" items including a live Meridian widget and
is configurable; Atlas is pleasant and capable for daily list/reminder use on web and kiosk with
FTS search; the Calendar offers month/week/day/agenda views, is reachable from every page, is
configurable, looks good, and shows all permitted node + standalone events with no double-writing.
Permissions enforced throughout; all three follow the shared design system; used daily.

---

## Milestone 3 — Home Wiki, Pets, Education

> **Owner re-prioritisation (2026-07-14, new university term).** Two changes:
> 1. **Education is pulled to the front of M3 and built now**, uni-first — the owner needs to
>    track **assignments, lectures/timetable and exams** this term. School-age-child features
>    (homework cards, reading logs, kiosk) follow once the uni slice is usable.
> 2. **Web/mobile daily use is the priority; kiosk is deferred.** Before/alongside Education,
>    run a **UX pass on the Calendar and Atlas (tasks/lists) for web and small screens** — they
>    are functionally complete (M2.5) but feel clunky for daily phone/laptop use. Kiosk polish
>    that was being treated as a priority is de-prioritised until the web/mobile core feels good.
>
> "Mobile" = the **responsive web app** (no native client yet; native stays deferred per D3, PWA
> is the likely first bridge). The Meridian revisit (M2 note above) is **paused**.
>
> **Scope resolved with owner (2026-07-14):** build **Education first**. **V1 = uni slice** —
> courses/subjects + assignments/exams (due dates → Calendar) + weekly lecture timetable; school-
> child/kiosk features follow. **"Tasks" = Atlas to-do lists** (improve those, no new task app).
> **"Mobile" = responsive-web polish only** (no PWA yet). Calendar/Atlas web-mobile polish runs
> after/alongside Education.

Round out everyday household value.

Build, one node at a time, each fully end-to-end (models → API → permissions → search via
Postgres FTS → calendar via the helper → Hub widgets → kiosk view where relevant → tests):
- **Home Wiki** — pages, categories, favourites, emergency info, kiosk-safe read view.
- **Pets** — profiles, treatment/vaccination reminders, vet appointments.
- **Education** — institutions, courses, assessments/homework, school events; kiosk homework
  cards.

**Done when:** each node delivers real daily value and the family reaches for HomeStack over
the old separate tools.

---

## Milestone 4 — Security maturation

Harden the sensitive-data machinery before any finance or health data goes in.

Build:
- Sensitive-node re-authentication (password-based, defined for web and kiosk) (D6).
- Audit coverage for sensitive access, permission changes, backups, sensitive downloads.
- Sensitive-node locking and the sensitivity dimension fully enforced through the resolver.
- Attachment permission checks (`visibility`/`sensitivity`) hardened (D11).
- Pre-remote-access checklist satisfied if you ever want VPN access (HTTPS, reverse proxy,
  rate limiting, strong admin passwords).

**Done when:** a sensitive node can be locked, re-auth works on web and kiosk, and access is
audited.

---

## Milestone 5 — Native Solace (D13, D14)

Now that sensitive machinery exists, migrate finance in natively.

Build:
- Native Solace node on shared services; `sensitivity = financial`; re-auth required; hidden
  from children/users by default; access audited.
- Reuse the proven bill-recurrence and payday-checklist logic; rebuild the shell.
- One-time import of the household's live Solace data.

**Done when:** only authorised users reach Solace, finance never leaks into unauthorised Hub/
Calendar/Search/kiosk views, and the standalone Solace app is no longer needed at home.

---

## Milestone 5.5 — Home Assistant bridge (important; D22)

Build after the current household pilot, remaining M4 security work and Solace production
cutover validation. This is a dedicated **Home Assistant node**, not a generic integrations or
plugin framework. Full specification: `26_Node_Home_Assistant.md`.

The non-negotiable ownership rule is: **Home Assistant owns devices, entities, live state,
history, areas and automations; HomeStack owns household records, people, tasks, Calendar data,
permissions and presentation mappings.** Neither side copies the other's durable domain data.

### 5.5.0 — Contract and security gate

- Confirm network reachability from the HomeStack backend container to the local Home Assistant
  REST API and record the supported URL/TLS arrangement.
- Add a dedicated `apps/home_assistant` node and `home_assistant.*` permissions; do not create a
  generic `integrations` app and do not embed Home Assistant in an iframe.
- Keep the Home Assistant base URL and long-lived access token in deployment secrets/environment,
  never browser code, ordinary node settings, API responses, logs or audit metadata.
- Define explicit entity and action allowlists. Locks, alarm panels, covers/garage doors and
  cameras are read-only or absent until their separate safety/privacy review.
- Define request timeouts, bounded response sizes, connection-health reporting, TLS verification,
  safe URL validation and redaction. Write permission/security tests first (D10).

**Gate:** a backend-only connection test can authenticate, fetch Home Assistant configuration and
fail safely when Home Assistant is unavailable or the token is invalid.

### 5.5.1 — Read-only Home Status V1

- Implement a small REST client for Home Assistant state/config endpoints. Fetch only explicitly
  mapped entities; do not mirror all entity states or recorder history into PostgreSQL.
- Add household-scoped entity mappings: Home Assistant `entity_id`, friendly HomeStack label,
  display group/order, icon/colour override, kiosk-safe flag and visibility. All models use
  `HouseholdBaseModel`.
- Build admin mapping/discovery UI with search and preview; discovery is read-only and never
  imports devices automatically.
- Ship a responsive **Home Status** page and Hub widget for useful glanceable state such as doors,
  temperature, humidity, lights, energy/solar/battery and presence-safe summaries.
- Use short in-process/request caching and clear stale/offline states. Do not add Redis/Celery
  solely for this node (D5).

**Gate:** selected entities render quickly on phone/desktop, unavailable entities degrade clearly,
and no Home Assistant token or unmapped entity leaks to the client, Search, kiosk or audit logs.

### 5.5.2 — Safe controls

- Add an explicit allowlist of callable actions (`domain.service` + permitted entity targets and
  bounded fields). Do not accept arbitrary service names or raw payloads from the browser.
- Start with low-risk lights, switches, fans, scenes and scripts. Provide optimistic UI only where
  the resulting state can be reconciled safely.
- Enforce `home_assistant.control` through the central resolver and audit every attempt/result.
  Sensitive controls require adult permission and password re-auth; child/kiosk controls are
  separately opt-in per action.
- Add confirmation, timeout, error and offline behavior; never claim success until Home Assistant
  accepts the service call.

**Gate:** an authorised adult can run allowlisted controls from phone/desktop, denied roles and
tampered payloads fail in backend tests, and every control is attributable in the audit log.

### 5.5.3 — HomeStack events into Home Assistant automations

- Subscribe inside the dedicated node to approved HomeStack domain events through the thin D4
  interface; other nodes never import Home Assistant code.
- Translate only configured events to namespaced Home Assistant events such as
  `homestack_maintenance_completed`, with minimal non-sensitive payloads and stable record links.
- Provide event-mapping UI, test-fire support and delivery audit/health. Delivery happens after
  the owning transaction commits, fails independently, and uses only bounded immediate retry;
  no durable event-bus table, replay queue or broker is introduced.
- Document example Home Assistant automations, including announcements, dashboard refreshes and
  safe reminders.

**Gate:** at least three real household workflows run reliably without duplicating HomeStack
records or exposing finance/private data in Home Assistant event payloads.

### 5.5.4 — Real-time state push (conditional follow-up)

- Add the Home Assistant WebSocket API only if measured REST refresh latency is inadequate.
- Run any persistent subscriber as a supervised, reconnecting management-command/service process;
  do not hide a forever loop inside web workers and do not add Redis/Celery by default.
- Subscribe only to mapped entities, coalesce bursts, reconnect with backoff and expose stale/
  disconnected health. Live state remains ephemeral rather than copied into durable tables.

**Gate:** reconnect/restart behavior is proven on the home server and loss of Home Assistant never
blocks ordinary HomeStack pages.

### 5.5.5 — Optional Home Assistant custom component

- Build `custom_components/homestack` only if Home Assistant genuinely needs to consume HomeStack
  as native sensors/calendar/to-do entities. This is not required for Home Status V1.
- Before implementation, make an explicit security decision for a narrowly scoped machine
  credential or signed webhook. Do not weaken D6 by exposing ordinary session or user tokens.
- Expose read-only entities first; every entity reads HomeStack's existing API/service layer and
  does not create a second source of truth. Add writes only for individually reviewed actions.
- Provide config flow, unload/reload handling, diagnostics with secret redaction, version
  compatibility tests and install/upgrade documentation.

**Gate:** the component survives Home Assistant restart/reload, exposes only authorised mapped
data and can be removed without losing any HomeStack or Home Assistant domain records.

**Milestone done when:** phases 5.5.0–5.5.3 are accepted in daily use: selected smart-home state is
useful on the HomeStack Hub, safe controls are permissioned/audited, approved HomeStack events can
drive Home Assistant automations, both systems remain usable when the other is offline, and there
is no duplicated ownership. Phases 5.5.4–5.5.5 remain evidence-driven extensions.

---

## Milestone 6 — Remaining nodes (as appetite allows)

**Fitness & Training shipped as an owner-requested vertical slice (2026-08-10, D24).** It is
separate from medical Health and includes the exercise/program/live-session/records/social loop.

Each built end-to-end, one at a time, in roughly this order:
**Inventory → Assets → Hearth → Travel → Projects → Health.**

- Inventory and Assets pair naturally (consumables vs. owned items).
- Hearth benefits from Inventory existing (pantry checks, grocery generation via Atlas).
- **Health is last** and only after security maturation is proven (it already is, post-M4);
  all Health data sensitive by default.

**Done when:** each node meets its completion criteria in its node spec.

---

## Milestone 7 — Infrastructure as needed

Add only when a feature demands it (D5):
- Redis + Celery + Celery-beat once reminders/background work outgrow the cron management
  command.
- Push/email notification channels.

**Done when:** background-dependent features work reliably; not before.

---

## Milestone 8 — Productization (only if it's genuinely good)

Pursue only after HomeStack has fully replaced Meridian and Solace for your household and is
used daily — that daily use is the proof it's worth releasing.

Consider:
- A clean install/onboarding flow and self-host setup docs.
- First-run wizard (create household, admin, enable nodes).
- A PWA as the first phone bridge (D3), before committing to native app tech.
- Licensing decision and a public repo/release.
- Confirm the **self-hosted** model (D2) — no SaaS, no custody of others' data.

### 8.1 — Household-portable floor-plan builder (future Homestead feature)

**Why here:** the current native plan proves the viewing and room-linking experience, but its
geometry describes one particular house. Another household must be able to create or update its
own plan without changing source code. This belongs inside Homestead and is an important part of
making a self-hosted release usable by somebody other than its original household. It is a warm,
approximate household planner — **not** CAD, a survey tool or a construction drawing.

**What users see:** Homestead → Rooms keeps the calm interactive viewer. Authorised editors gain
an **Edit floor plan** action that opens a larger desktop/tablet workspace:

```text
┌──────────────────────────────────────────────┬──────────────────────┐
│                                              │ Selected area        │
│               Drawing canvas                │ Name: Kitchen        │
│                                              │ Linked room: Kitchen │
│       [Bedroom] [Bathroom]                   │ Width / height       │
│       [       Living room       ]            │ Colour / icon        │
│                                              │ Delete / duplicate   │
├──────────────────────────────────────────────┴──────────────────────┤
│ Select · Draw room · Door · Window · Undo · Redo · Preview · Save │
└─────────────────────────────────────────────────────────────────────┘
```

On first use, offer **Blank canvas**, a small set of basic house/apartment shapes, **Upload a plan
to trace**, or duplicate an existing floor. Users draw, drag and resize areas; snap shared walls;
add doors/windows/stairs and outdoor areas; then link an area to an existing Homestead room or
create a room while drawing. A linked area always derives its display name, icon and colour from
that room. Dimensions are optional labels, not claims of construction accuracy. Phones retain an
excellent viewer and small corrections; serious drawing is intentionally desktop/tablet-first.

**Storage and ownership:** replace the code-level `AREAS` definition with household-scoped
`FloorPlan`, `FloorPlanArea` and `FloorPlanFeature` records. A plan stores its name, level, canvas,
optional tracing image and draft/published state. An area stores rectangle/polygon geometry,
type, order and a nullable real FK to `RoomArea`. Features store doors, windows, stairs, labels
and their position/rotation. The room FK replaces `floorplan_data.floorplan_slot` as the durable
relationship; renaming a room is therefore safe. Convert the current house drawing into the
first saved plan during migration, while fresh installs begin with onboarding rather than this
house's geometry. All records remain household-scoped and use existing `homestead.*` permissions.

**Delivery slices:**

1. **Core authoring:** blank canvas, rectangular areas, move/resize, grid snapping/alignment,
   room link/create, multiple levels, zoom/pan/fit, undo/redo, autosaved draft and explicit
   publish/preview.
2. **Trace and describe:** upload/crop/rotate a reference image with adjustable opacity; add
   polygons, doors, windows, stairs, outdoor areas and reusable starter templates. The source
   image may be hidden or removed once tracing is complete.
3. **Confidence and portability:** revision history/restore, duplicate plan/floor, safe deletion
   of linked areas, accessible keyboard editing, responsive viewer, install/onboarding guidance
   and import/export of the plan document.
4. **Optional assistance only after the editor works:** image-to-plan suggestions may propose
   walls and labels, but never publish automatically. OCR/AI remains outside the core dependency
   and every suggestion must be editable.

**Gate:** on a clean install, a second household can create a multi-area plan from blank or by
tracing an upload, link/create rooms, publish it, reload it on phone and laptop, rename a linked
room without breaking the plan, restore the previous revision and complete the workflow without
developer assistance or source-code edits.

### 8.2 — Corners: activity, assignments, personal lists and wishes

**Initial slice shipped in v0.31.0.** Remaining polish is pagination/load-more, avatar links from
every source surface and any later owner-approved interaction types.

Add household-facing `/corners/:personId` pages, distinct from administrator account management.
The owner sees **My Corner** and other pages use **Alex's Corner**-style real names. Each Corner
has Overview, Activity, Assigned and Lists & wishes tabs. Enabled nodes contribute
permission-filtered projections through a registry: completed Fitness sessions/PBs, Meridian
tasks/rewards/routines, Atlas additions/completions, Homestead room planning and later node work.
The Assigned tab gathers active work without moving ownership from its source node.

Atlas owns ordinary personal shopping and point-free wish lists; add a Person owner plus a
wishlist list type. Homestead room products and the existing points-based Meridian child wishlist
remain in their original nodes and are displayed under clearly labelled sections—never copied.
New personal lists default household-visible with a Private option, subject to owner confirmation.
Visibility, enabled-node access and sensitive-node contracts apply before aggregation. Implement
in the delivery slices and acceptance gate defined in `28_Core_Corners.md`.
Owner decisions now fix household-visible as the default, a 30-day initial Activity window and a
suggestion/accept/dismiss workflow instead of direct edits to another person's list. Recommended
social follow-ups include **owner-approved emoji reactions** (heart, thumbs-up, celebration and
other friendly emoji), short moderated comments, offer-to-help requests
that require assignment approval, and optional list watching. Gift reservation is explicitly
later because hiding it from the recipient adds a special privacy rule.

### 8.3 — Safe shared URL import and enrichment

**Product slice shipped in v0.31.0.** Hearth recipe extraction remains tied to the future Hearth
schema; retailer-specific adapters are evidence-driven follow-ups, not a headless-browser goal.

Add a backend-only preview service so a pasted public product URL can propose title, shop, price,
currency and image for Homestead room products and Atlas shopping/wish items. Later, a separate
Hearth adapter reads Schema.org Recipe data into editable ingredients, ordered method steps,
times, yield, image and source attribution. Users review and correct every draft before saving;
manual entry always remains available, and imported values never silently overwrite edits.

This feature starts with its security boundary: block SSRF to localhost/LAN/container/metadata
addresses across DNS and redirects; cap time/size/content types; rate-limit; never forward cookies
or credentials; and safely handle image retrieval. Prefer JSON-LD, then Open Graph, then narrow
fallbacks. JavaScript/authenticated/bot-blocked pages may return partial results rather than adding
a headless browser. Full UX, provenance, image-cache choice, delivery slices and acceptance tests
are specified in `29_Core_Link_Import.md`.
Confirmed images are copied locally through the bounded safe fetch/media path. Imported price is a
user-confirmed snapshot, while an optional watch stores separate observations. An idempotent cron
job checks watched wishes once after approximately 09:00 in Household local time and notifies the
owner/watchers only for a new explicit sale, meaningful drop or target-price hit—never repeatedly
for the same unchanged offer and never by silently changing a chosen/actual cost.

**Done when:** another household could install and run HomeStack from your docs without you.

---

## What is explicitly NOT on this roadmap for now

Native mobile/desktop apps, full offline mode, OCR/AI, a general plugin system, public internet
exposure, external calendar sync, field-level encryption, and any multi-household/SaaS
behaviour. These stay in the Parking Lot until the core product earns them.

> Note (2026-07-14): the owner's "web/mobile" priority means **responsive-web** quality on phones
> and laptops — **not** a native app. A **PWA** (installable/offline shell) is the sanctioned first
> bridge (D3, M8) and may be pulled earlier if daily phone use warrants it; native apps remain off
> the roadmap.
