# Document 1 — Master Software Specification (MSS)

> Canonical. Supersedes all earlier MSS versions. See `00_README_and_Changelog.md` for decisions.

## 1. Purpose

HomeStack is a secure, modular, self-hosted household management platform that provides one
central place to run household life. It replaces the scattered apps, documents, calendars,
lists and reminders a family currently juggles with a single, coherent, family-oriented
system.

It is built first for one household — two adults and two children, on an always-on home
server — and designed so that, if it proves genuinely good, it could later be released as a
**self-hosted** product other families run themselves. That ambition shapes which technical
decisions are treated as permanent (see §3); it does not expand the initial scope.

## 2. Vision

HomeStack should feel like one warm, approachable system rather than a collection of
separate applications. The Hub answers "what needs attention today?", the Calendar is the
household's shared timeline, and a touchscreen kiosk turns the system into a family
information centre everyone — including the kids — can use comfortably.

Long-term platform reach (web → kiosk → PWA → native apps) is enabled by an API-first
backend, but only the web and kiosk experiences are in early scope.

## 3. Core design philosophies

**Security first.** HomeStack holds sensitive household information — finances, health
notes, documents, children's details. Security is a built-in feature, not an afterthought:
role-based and backend-enforced permissions, sensitive-node re-authentication, audit logs,
secure PIN/password storage, session management and protected backups. (See the Security
Architecture document.)

**Modular and opt-in.** A fresh install includes only core services, Hub, Calendar, user
management and settings. Every node is enabled deliberately by an administrator. Nodes can
be enabled, disabled, hidden, locked, permission-restricted or kiosk-restricted.

**Flexible tracking depth.** Users are never forced to record more than they want. Each
node supports basic, standard and detailed use, and remains useful with only one or two
fields filled in.

**Family-oriented experience.** Friendly, warm, visual, touch-friendly, consistent, and
child-appropriate where relevant. It must never feel like enterprise software.

**Kiosk as a first-class platform.** A permanently available household touchscreen (tablet,
Surface, Raspberry Pi display, wall-mounted screen) is a primary surface, with avatar login,
PIN entry, ambient mode, large touch targets and permission-safe displays.

**API-first.** Business logic lives in the backend; all clients share one API. This is the
hinge that keeps native apps — and a possible PWA bridge — open without backend rework.

**One household per install.** HomeStack runs a single household. The schema carries a tenant
column for future-proofing (see Architecture/Database docs), but no multi-household behaviour
is built.

## 4. Confirmed node model

Nodes are broad areas of household life with their own workflows, records, permissions and
Hub/Calendar behaviour — not small features.

**Core platform services** (always present, not optional):
Hub · Calendar (app name: `scheduling`) · People · Notifications · Search ·
Documents/Attachments · Permissions · Settings · Backups.
*(The durable Event Bus from earlier drafts is deferred; node decoupling uses signals — see Architecture doc.)*

**Confirmed opt-in nodes:**
Atlas · Home Wiki · Pets · Education · Inventory · Assets · Hearth · Travel · Projects ·
Health · Meridian · Solace.

### 4.1 Consolidation rules (unchanged, still in force)

These do **not** become standalone nodes:

- Vehicles, warranties, appliances, tools, home maintenance → **Assets**
- Subscriptions → **Solace**
- Documents → core **Documents/Attachments** service
- Garden → **Projects** or **Inventory** by context
- People → core service
- Library → parked unless it outgrows simple asset tracking
- Fitness → parked under Health/future
- Smart Home → future integration

### 4.2 Node decision rule

A future feature becomes a new node only if it represents a major household domain, has its
own data model and workflows, needs its own permissions, appears uniquely on Hub/Calendar,
would overload an existing node if absorbed, and would be independently useful. Otherwise it
is a feature inside an existing node.

## 5. User roles

- **Admin** — full access; manages users, permissions, nodes, settings, backups, audit logs;
  reaches sensitive areas after re-authentication.
- **Manager** — trusted adult; manages most household information and nodes; reaches Solace/
  Health only if granted.
- **User** — standard household member; uses permitted nodes, Hub widgets and Calendar events;
  avatar/PIN login.
- **Guest** — optional, disabled by default (house/pet sitter); never sees sensitive data by
  default.

Identity note: a **user** has a login and owns/audits records; a **person** is a household
profile (adult, child, or non-login member) and is the subject/assignee of records. Many
members are both.

## 6. Authentication (summary)

Avatar + PIN for everyday login (web and kiosk), backed by Django sessions. Admin/manager
accounts also have passwords. Sensitive nodes (Solace, Health, sensitive Documents) require
re-authentication using a password rather than the PIN. Token auth is added when native apps
arrive. Full detail lives in the Security Architecture document.

## 7. Core platform services (responsibilities)

- **Hub** — the landing page; "what needs attention today?"; configurable, permission-aware
  widgets.
- **Calendar** — the household timeline; all nodes may contribute events through one shared
  generation helper (nodes own their dates).
- **People** — member profiles used across nodes.
- **Notifications** — in-app reminders now; push/email later.
- **Search** — global, permission-aware, via Postgres full-text search.
- **Documents/Attachments** — shared file service used by all nodes; sensitive files get
  stronger controls.
- **Permissions** — central, backend-enforced access control.
- **Settings** — household, user, theme, widget and node settings.
- **Backups** — manual and scheduled backup *and a defined restore path*.

## 8. Confirmed nodes (summary)

Full per-node specs are separate documents. In brief:

- **Atlas** — notes, to-do/grocery/shopping lists, checklists, simple reminders, quick capture.
- **Home Wiki** — persistent household knowledge: WiFi, emergency info, procedures, manuals,
  bin schedules, kiosk-safe reference pages.
- **Pets** — profiles, treatment/vaccination reminders, vet appointments, medication, pet
  documents and care instructions.
- **Education** — school and university: courses, assessments, homework, exams, timetables,
  events, permission slips.
- **Inventory** — consumables and stored items with low-stock and expiry alerts.
- **Assets** — vehicles, appliances, tools, warranties, service history, maintenance and
  registration reminders, documents.
- **Hearth** — recipes, meal plans, "dinner tonight", grocery generation.
- **Travel** — trips, bookings, itineraries, packing, countdowns.
- **Projects** — large household initiatives with tasks, milestones, notes, attachments.
- **Health** — sensitive human health: appointments, medications, allergies, immunisations,
  records. Built only after the security foundation is mature.
- **Meridian** — household tasks, rewards and points; kid-facing kiosk experience. Becomes a
  **native node early**.
- **Solace** — bills, budgets, planned purchases, subscriptions; sensitive, re-auth required.
  Becomes a **native node after security maturation**.

Meridian and Solace already exist as working applications in the household. They are migrated
in natively (shell rebuilt on shared services, proven logic reused, live data imported) — no
external-link/iframe layer is built.

## 9. Version 1 scope

V1 is deliberately small. It is reached in stages (see Roadmap), but the V1 *system* is:

- Core platform: Docker stack, session auth (avatar/PIN + admin passwords), Users + People,
  central permissions, Settings, Backups (with restore), audit logs.
- Hub + Calendar with the shared event-generation helper.
- Kiosk shell (ambient mode, avatar login, timeout).
- **Atlas** as the first node.
- **Meridian** migrated native.
- **Home Wiki, Pets, Education.**

V1 does **not** include: Inventory, Assets, Hearth, Travel, Projects, Health, native Solace
(these follow), nor native mobile/desktop apps, offline mode, OCR/AI, plugin system, public
internet exposure, external calendar sync, or field-level encryption.

## 10. Success criteria

HomeStack succeeds when, for this household:

- The Hub clearly shows what matters today and the Calendar acts as the shared timeline.
- The kiosk is useful and the kids reach for it.
- Everyone sees only what they're permitted to; sensitive data stays protected.
- Nodes feel visually consistent — one platform, not many apps.
- The node list stays deliberate and manageable.
- Atlas, Home Wiki, Pets, Education and native Meridian deliver real daily value, and the
  family reaches for HomeStack instead of the old separate apps.

The path to a sellable product runs *through* a great product for this household: if HomeStack
genuinely replaces Meridian and Solace for the family and gets used daily, that is the proof
it is worth releasing.
