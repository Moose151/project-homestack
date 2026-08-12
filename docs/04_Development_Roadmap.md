# Document 4 — Development Roadmap

> **Canonical roadmap.** This document tracks current sequencing and future gates, not the full
> implementation diary. Completed release detail belongs in `VERSION_HISTORY.md`; current
> operational state belongs in `HANDOVER.md`.

## 1. Guiding principle

Build vertically and finish real household workflows before expanding the domain count. New work
should improve one of four things:

1. everyday household usefulness;
2. reliability/operability of the live installation;
3. security/privacy of existing data;
4. a clearly justified missing household domain.

Do not add infrastructure or nodes because they are conventionally expected. Add them when the
current design has a demonstrated limit.

## 2. Completed foundation

The following roadmap stages are **complete** and should not be treated as active work:

| Stage | Status | Result |
|---|---|---|
| M0 Planning | Complete | Canonical architecture/node/security documentation and decisions D1–D24. |
| M1 Walking skeleton | Complete | Docker stack, auth, People, permissions, audit, backup/restore, Atlas, Hub, Calendar, kiosk. |
| M2 Meridian | Complete / in daily use | Native Meridian source of truth, adult cockpit, kid workflows, rewards/points/approvals. |
| M2.5 Core surfaces | Complete | Functional responsive Hub, Atlas and Calendar with FTS, widgets, views and shared scheduling. |
| M3 Education/Home Wiki/Pets | Complete | All three nodes shipped end-to-end. |
| M4 Security maturation | Functionally complete | Generic sensitive-node re-auth/locks, permission-aware attachments, audit coverage and kiosk-safe sensitive access. |
| M5 Solace | Complete / in daily use | Native Money/Solace feature set; household chose fresh manual bill entry rather than legacy data import. |
| Homestead expansion | Complete baseline | Property, maintenance, appliances, cover/costs, rooms/plans, pools/spas, utilities and interactive floor plan. |
| Fitness & Training | Complete / in use | D24 social training node separate from medical Health. |
| Corners + safe link import | Complete baseline | Person-centred summaries, lists/wishes/reactions and bounded URL preview/cache/watch capability. |
| Daily coordination | Complete except push | Appointments, Agenda, dated Atlas sync, birthdays/People and editable pool schedules shipped. |
| Travel baseline | Complete | Trips/ideas, booking/cost planning, itinerary/Things to do, Calendar/notification/Corner integration. |
| Grocery + Shopping | Complete | Dedicated shared Atlas Grocery and Shopping surfaces. |
| LAN HTTPS | Complete | Trusted `https://homestack.moosesoftwares.com` via Nginx Proxy Manager + Cloudflare DNS challenge + Pi-hole local DNS. |

Historical sub-phases and release numbers are intentionally omitted here; see `VERSION_HISTORY.md`.

## 3. Active milestone — PWA notifications / Web Push

**Status:** active implementation work as of 2026-08-12.

Canonical specification: `32_Core_Notifications_and_Push.md`.

### Goal

Turn the existing in-app notification capability into useful per-person phone notifications over
the now-trusted HTTPS origin, without leaking sensitive details to lock screens or creating a
second notification source of truth.

### Required outcomes

- installable/responsive PWA behaviour where required for target devices;
- per-user notification preferences by category;
- per-device Web Push subscriptions;
- VAPID/Web Push delivery from the backend;
- quiet-hours and lead-time behaviour;
- safe sparse payloads, especially for financial/health/private records;
- tap/deep-link back into the owning HomeStack record;
- permission re-check when the notification is opened;
- subscription expiry/unregister handling;
- tests for cross-user isolation and sensitive payloads.

### Done when

At least two household users/devices can independently opt into different notification categories,
receive a real push while HomeStack is not open, tap it into the correct permitted location, and
no sensitive record detail is exposed to an unauthorised or locked surface.

Do not merge an alternative notification architecture into this roadmap while the dedicated push
branch is in progress; reconcile this document to the actual shipped implementation after that
branch lands.

## 4. Near-term engineering milestone — production operation hardening

This should be treated as the next major engineering stream alongside/after push, before public
remote access is considered.

### 4.1 Production serving

The current live stack still uses development servers in the containers. Establish a supported
production deployment profile:

- Django served by a production WSGI server (for example Gunicorn);
- frontend built with `vite build` and served as static assets rather than the Vite dev server;
- static/admin asset handling explicitly solved;
- preserve Nginx Proxy Manager as the external LAN TLS/reverse-proxy layer unless there is a
  concrete reason to replace it.

### 4.2 Docker network exposure

Move internal services toward private container networking:

- PostgreSQL should not require a LAN-exposed host port;
- Django/frontend should be reachable from NPM through an explicit shared Docker network rather
  than broadly published host ports where practical;
- NPM admin (`81`) remains LAN/admin-only and is never publicly exposed.

Keep a development Compose profile/override that exposes developer-friendly ports where useful.

### 4.3 Deployment automation

Create one supported deployment command/script that performs the required sequence safely:

1. preflight/working-tree checks;
2. optional/current backup;
3. image build;
4. migrations;
5. service recreation/restart;
6. backend health check;
7. frontend/HTTPS smoke check;
8. clear failure output and rollback guidance.

This exists to remove recurring human errors such as pulling new code without rebuilding or
forgetting a migration.

### 4.4 CI and frontend automated testing

Add CI when practical for:

- backend tests;
- migration drift (`makemigrations --check`);
- frontend typecheck;
- frontend production build;
- frontend unit tests for critical state/components;
- a small Playwright suite for login, permissions, Hub/Calendar and sensitive re-auth flows.

### Done when

The live installation no longer depends on development servers, internal database/app ports are no
more exposed than necessary, and a routine update can be applied through one documented command
with automated smoke validation.

## 5. Reliability milestone — backups and system health

HomeStack is becoming household infrastructure, so operational recovery matters more than adding
another minor feature.

### 5.1 Off-server encrypted backup

Extend the existing tested backup/restore system so at least one encrypted copy lives off the
primary server/storage device. Requirements:

- retain database + media consistency and checksums;
- protect backup credentials/keys outside ordinary user-facing settings;
- keep restore documentation current;
- periodically perform a real restore test, not just backup creation.

### 5.2 System Health surface

Add an admin-focused HomeStack system-health page only if it can remain simple. Candidate data:

- installed HomeStack version;
- backend/database health;
- free disk/storage condition;
- last successful HomeStack backup and off-server copy status;
- scheduled-command last-run/failure status;
- push dispatcher status once shipped;
- Home Assistant bridge health once shipped;
- links to existing external operations tools (for example Uptime Kuma/Dozzle) rather than
  rebuilding those tools inside HomeStack.

### Done when

A server/storage failure has a credible tested recovery path and an administrator can see whether
core scheduled/backup functions are healthy without reading container logs for routine checks.

## 6. Security gate before any public remote access

Public internet reachability remains **not enabled**.

Before Cloudflare Tunnel or direct public access is approved, satisfy the authoritative checklist
in `05_Security_Architecture_Document.md`, including at minimum:

- production-serving path;
- trusted HTTPS (already present on LAN);
- strong adult/admin passwords;
- sensitive-node re-authentication and permission tests (already present);
- rate limiting/brute-force controls;
- 2FA/passkey capability for adult/admin remote access;
- protected/off-server backups;
- reviewed secure-cookie/proxy production settings;
- explicit public-exposure threat-model review.

A VPN-only remote path may remain the preferred option even after the checklist is satisfied.

## 7. Milestone 5.5 — Home Assistant bridge (important, D22)

**Sequence:** after working push notifications; do not build a generic integrations platform.

Canonical specification: `26_Node_Home_Assistant.md`.

### 7.1 Contract/security gate

- backend-only URL/token secret;
- prove backend-container reachability;
- explicit entity/action allowlists;
- timeouts, bounded responses, redaction and TLS/URL validation;
- permissions/security tests first;
- locks/alarms/cameras/garage/safety-critical controls absent or read-only until separately
  reviewed.

### 7.2 Read-only Home Status

- map selected Home Assistant entities only;
- no PostgreSQL mirror of all device state/history;
- responsive status surface + Hub widget;
- short cache and explicit stale/offline presentation.

### 7.3 Safe controls

- only stored server-side allowlisted actions;
- central permissions and audit;
- no arbitrary domain/service/entity requests from the browser.

### 7.4 HomeStack events into automations

- publish only approved minimal HomeStack domain events;
- namespaced Home Assistant event types;
- do not duplicate owning records in Home Assistant.

WebSocket state push and a custom Home Assistant component remain conditional follow-ups.

### Done when

HomeStack can reliably show selected household-relevant HA state, execute a small reviewed set of
safe actions, and trigger useful approved automations while either system can be offline without
corrupting or blocking the other.

## 8. Everyday feature priorities after reliability work

### 8.1 Hearth

Hearth is the strongest remaining everyday household domain:

- recipes;
- meal planning;
- dinner/meal view;
- safe recipe import;
- ingredient scaling;
- send missing ingredients into the existing **Atlas Grocery** list.

Do not create a second grocery store/database.

### 8.2 Travel finishing slices

Only where useful in real trips:

- packing lists;
- protected travel documents;
- richer photo/journal/map/flight integrations later.

The itinerary itself is already shipped.

### 8.3 Homestead/Assets/Inventory consolidation

The capability-toggle proposal in `31_Core_Manage_HomeStack.md` remains **a proposal**, not an
implemented fact. Revisit only after current navigation/domain use shows that separate Home Wiki,
future Inventory or future Assets would actually create clutter.

No data should be moved or schemas merged merely to reduce menu entries.

## 9. Health milestone — deliberately later

Medical Health is valuable but carries the highest privacy cost. Start only after the production,
backup and adult-authentication posture is stronger.

Health must remain separate from Fitness & Training (D24). Candidate scope:

- medical appointments/providers;
- medication/prescription tracking;
- allergies/immunisations;
- protected medical notes/documents;
- emergency health information with carefully reviewed visibility.

## 10. Native clients / offline

PWA is the first phone bridge. Do not choose React Native/Tauri/other native technology until the
responsive/PWA product proves what capabilities are actually missing.

Native apps should reuse the existing API/business/permission model rather than introduce a second
backend or local source of truth.

## 11. Evidence-gated future work

Only pursue when real household use demonstrates the need:

- top-level Projects node;
- standalone Inventory node;
- standalone Assets node;
- Redis/Celery;
- durable event broker;
- generic integrations/plugin system;
- semantic/AI search;
- OCR;
- external calendar sync;
- full offline conflict-resolution architecture.

## 12. Current sequencing summary

As of 2026-08-12:

1. **Finish Web Push/PWA notifications** (active branch/workstream).
2. **Production-serving/deployment/network hardening.**
3. **Encrypted off-server backup + basic operational health.**
4. **Home Assistant M5.5.**
5. **Hearth / other everyday feature work according to household demand.**
6. **Health only after stronger operational/authentication maturity.**
7. **Public remote access only after its security gate — not as an automatic next step.**

Real household feedback can reorder feature milestones, but should not bypass security or recovery
gates.