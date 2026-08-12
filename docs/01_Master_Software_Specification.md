# Document 1 — Master Software Specification (MSS)

> **Canonical product specification.** Architectural decisions live in
> `00_README_and_Changelog.md`; implementation status lives in `HANDOVER.md`; historical release
> detail lives in `VERSION_HISTORY.md`. This document describes what HomeStack *is* and the
> boundaries that should remain stable as it grows.

## 1. Purpose

HomeStack is a secure, modular, self-hosted household management platform for one household. It
replaces scattered household apps, lists, calendars, documents and reminders with one coherent
system built around a shared Hub, Calendar, People directory and a deliberate set of opt-in
household domains.

It is built first for the household that runs it. If it later becomes a product, the intended
model is still **self-hosted, one household per installation**, not SaaS.

## 2. Product vision

HomeStack should feel like one warm, approachable household operating system rather than a set of
unrelated apps. The important surfaces are:

- **Hub** — what needs attention today.
- **Calendar** — the household timeline.
- **People** — the shared identity/subject layer used across domains.
- **Responsive web app** — the primary everyday adult/mobile surface.
- **Kiosk** — a shared, permission-safe family surface, especially for children.
- **Corners** — person-centred views of assignments, activity, lists and wishes.
- **Opt-in nodes** — major household domains with their own workflows and permissions.

The backend is API-first so PWA/native clients can be added without rebuilding business logic.

## 3. Stable design principles

**Security first.** HomeStack stores finances, personal information, documents and potentially
health data. Permissions are backend-enforced, sensitive areas re-authenticate, protected access is
audited, and clients are never trusted as the security boundary.

**One household per install.** Every user-facing model remains household-scoped for structural
consistency and future self-hosted portability, but HomeStack does not implement SaaS tenancy,
sign-up or billing.

**Modular monolith.** Domains are separate Django apps within one backend. Shared capabilities live
in core services. Do not introduce microservices or cross-node model coupling without a demonstrated
need.

**Nodes are domains, not features.** A feature normally belongs inside an existing domain. New
nodes require clear independent workflows, data, permissions and household value.

**One source of truth.** Calendar events, Hub summaries, Corners and cross-node views project data
from the owning record instead of creating parallel competing records.

**Flexible depth.** A household can track the minimum useful information or progressively add
more detail. Detailed tracking must not be mandatory for basic use.

**Family-oriented UX.** Responsive, touch-friendly, understandable to non-technical household
members, consistent across nodes, and safe for children.

## 4. Core platform services

These are platform capabilities rather than optional household domains:

- **Hub** — permission-aware configurable widgets and daily summaries.
- **Calendar (`scheduling`)** — standalone events plus projections from dated node records.
- **People** — household members/profiles; separate from login Users.
- **Notifications** — in-app notification store and delivery preferences; Web Push is the current
  expansion path.
- **Search** — global permission-aware search over owning node querysets.
- **Documents/Attachments** — shared protected file capability used by domain records.
- **Permissions** — central roles, per-user overrides, visibility and sensitivity enforcement.
- **Settings / Manage HomeStack** — household, node, user and presentation configuration.
- **Backups** — backup creation plus a defined and tested restore path.
- **Audit** — immutable security/administrative activity records.
- **Events interface** — thin in-process publish/consume boundary based on Django signals (D4), not
  a durable broker or user-facing service.

## 5. Current node model

### 5.1 Shipped / active domains

- **Atlas** — household notes, to-dos, Grocery, Shopping, checklists, reminders, Agenda and shared
  everyday capture.
- **Meridian** — tasks, routines, points, rewards, approvals, goals, wishes and achievements;
  HomeStack is the source of truth and adult/admin cockpit.
- **Education** — institutions, academic profiles, courses, assessments, timetable/classes and
  education events.
- **Home Wiki** — persistent household knowledge, favourites and emergency/kiosk-safe reference.
- **Pets** — pet profiles, recurring treatments/reminders and appointments.
- **Books** — shared household Book catalogue, per-User Want to Read / Reading / Read shelves,
  personal ratings/notes and shared Book Clubs with ordered up-next queues.
- **Homestead** — home/property source of truth: rooms/areas, plans, maintenance, appliances,
  warranties, services, cover/cost context, pools/spas, utilities and floor plan.
- **Solace / Money** — bills, pay cycles, budgets/buckets, planned purchases and financial
  forecasting; sensitive and permission/re-auth protected.
- **Fitness & Training** — social training programs, live workouts, exercise history and personal
  records. It is intentionally separate from medical Health (D24).
- **Travel** — trips and ideas, participants, bookings/cost planning, itinerary/Things to do,
  Calendar/deadline integration and surprise visibility.

### 5.2 Important planned domain

- **Home Assistant** — a dedicated local bridge for selected state, safe allowlisted controls and
  approved HomeStack automation events. Home Assistant remains owner of devices, state, history
  and automations. HomeStack stores only household presentation/control/event mappings.

### 5.3 Deferred / evidence-gated domains

- **Hearth** — recipes, meal planning and generation of items into the shared Atlas Grocery list.
- **Health** — sensitive human medical information, deliberately separate from Fitness.
- **Inventory / Stock & storage** — still proposed as a Homestead capability rather than an
  automatic new top-level node.
- **Assets & vehicles** — non-home asset/vehicle scope; currently proposed as a protected
  Homestead capability unless real usage proves it needs an independent node.
- **Projects** — do not create as a top-level node until cross-domain project workflows materially
  exceed Homestead projects, Travel trips and Atlas lists.

### 5.4 Consolidation boundaries

- Home property, home appliances, warranties, home maintenance and home projects → **Homestead**.
- Household grocery/shopping → **Atlas**; Hearth may populate Grocery later rather than create a
  competing shopping store.
- Personal reading history and shared book-club workflows → **Books**; Education may later link to
  Books for course reading but does not own personal shelves/clubs.
- Finance/subscriptions → **Solace**.
- Documents → shared **Documents/Attachments**, linked to owning records.
- People → core **People**.
- Fitness/social training → **Fitness & Training**.
- Diagnoses, medications, injuries, measurements and medical notes → **Health** only.
- Smart-home device/state ownership → **Home Assistant**, with HomeStack only as a bounded bridge.

## 6. Users, People and roles

A **User** is a login identity and owns/audits actions. A **Person** is a household profile and is
the subject/assignee of household records. A Person may exist without a login.

Roles:

- **Admin** — full household administration; sensitive access still requires the relevant
  re-authentication gate.
- **Manager** — trusted adult with broad management capability, subject to explicit grants for
  sensitive domains.
- **User** — ordinary household member using permitted nodes and records.
- **Guest** — optional restricted role; disabled/unused unless deliberately configured.

Children use the same permission spine; child-safe behaviour is enforced by the backend, not by
hiding buttons alone.

## 7. Authentication and sensitive access

- Django session authentication for the current web/kiosk application.
- Avatar/PIN everyday login.
- Adult password credentials for re-authentication and administrative/sensitive operations.
- Argon2id password/PIN hashing.
- Short-lived elevated session state for sensitive-node access.
- HTTPS is now used on the LAN at `https://homestack.moosesoftwares.com` through the existing
  Nginx Proxy Manager and Pi-hole split/local DNS arrangement.
- Token/native-app authentication remains future work.

See `05_Security_Architecture_Document.md` for the authoritative security contract.

## 8. Cross-domain rules

1. Nodes do not import one another's models for business integration.
2. Cross-domain reactions use the thin events interface and shared services.
3. Node records own their dated information; Calendar projections use the scheduling helper.
4. Hub/Corners/Search are projections and must re-check source permissions.
5. `created_by`/`updated_by`/audit ownership references Users; assignee/subject references People.
6. Recurrence uses the established RRULE representation except the bounded rotating-schedule
   layer defined by D23.
7. Sensitive data must not leak into Calendar, Hub, Search, notifications, Corners or kiosk
   through derived representations.

## 9. Current product baseline

As of 2026-08-12, HomeStack is deployed on the home server and used in daily household workflows.
The foundational milestones, Meridian, core Hub/Atlas/Calendar surfaces, Education, Home Wiki,
Pets, **Books**, security maturation, native Solace, Homestead, Fitness, Corners/link import, daily
coordination, Travel, Grocery/Shopping and LAN HTTPS are implemented.

The current active product-development slice is **PWA/Web Push notifications**. Home Assistant is
intentionally sequenced after trusted HTTPS and working phone push notifications. Public internet
exposure has not been enabled.

Historical implementation detail does not belong in this MSS; use `VERSION_HISTORY.md` and Git
history for release chronology.

## 10. Success criteria

HomeStack succeeds when:

- household members use it because it is easier than the tools it replaces;
- the Hub and Calendar provide a dependable shared view of what matters;
- common tasks work comfortably on phone/laptop and shared kiosk surfaces;
- each record has one obvious owning domain;
- sensitive information remains protected in direct and derived views;
- the node model stays understandable rather than expanding for every feature;
- backup/restore and deployment are dependable enough that HomeStack can be treated as household
  infrastructure;
- future clients/integrations can use stable APIs without bypassing the existing permission and
  business-logic spine.

The path to any future self-hosted release runs through making the single-household installation
reliable and genuinely useful first.