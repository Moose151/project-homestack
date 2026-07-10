# HANDOVER.md — HomeStack

> **Read this first if you are a coding assistant.** It tells you what HomeStack is, the rules
> you must not break, what is done, and what to do next. Then read the canonical docs (below)
> before writing code. At the **end of every working session, append to the Progress Log** so
> the next assistant can continue cleanly.

---

## 1. What HomeStack is

A secure, modular, **self-hosted** household management platform for **one household** (two
adults, two children), run on an always-on home server via Docker Compose. It replaces scattered
apps with one warm, family-oriented system: a **Hub** ("what needs attention today?"), a
**Calendar** (the household timeline), opt-in **nodes** (areas of household life), and a
touchscreen **kiosk** the kids use.

Built solo. May *one day* be released as a **self-hosted** product other families run themselves
(never SaaS). That ambition only disciplines which decisions are permanent — it does not expand
current scope.

## 2. Canonical documentation (source of truth)

Read these in `docs/`. **If anything conflicts, this doc set wins.** Older `.docx` files are
archived/superseded — ignore them.

- `00_README_and_Changelog.md` — **all key decisions (D1–D18) with reasoning. Read this.**
- `01_Master_Software_Specification.md` — vision, node model, V1 scope.
- `02_Software_Architecture_Document.md` — architecture, base model, resolver, helpers.
- `03_Database_Design_Document.md` — schema and conventions.
- `04_Development_Roadmap.md` — milestones with "done when".
- `05_Security_Architecture_Document.md` — auth, permissions, sensitive nodes, kiosk.
- `06_API_Specification.md` — endpoints.
- `07_UIUX_Design_Guide.md` — design system, kiosk/child UX.
- `08_Coding_Standards_and_Project_Structure.md` — **how to write the code. Read this.**
- `09_Node_Model_Decision_Record.md` — why these nodes.
- `10_Future_Features_Parking_Lot.md` — what is deferred vs out of scope.
- `11`–`22_Node_*.md` — per-node specs (Atlas, Home Wiki, Pets, Education, Meridian,
  Inventory, Assets, Hearth, Travel, Projects, Health, Solace).
- `23_Core_Hub.md` — Hub core-service spec (aggregation surface, widgets, kiosk Hub). Read
  before the Atlas + Hub UX pass (§8).
- `24_Core_Calendar.md` — Calendar core-service spec (app `scheduling`, D7/D8 timeline,
  every-page access, configurable views, look & feel).
- `MILESTONE_1_Checklist.md` / `MILESTONE_2_Checklist.md` / `MILESTONE_2.5_Checklist.md` — the
  per-milestone build checklists. **M3 is next.**

## 3. Hard rules (do NOT violate these)

These are settled decisions. If you think one is wrong, **flag it in the Progress Log and ask —
do not silently override it.**

1. **Single household, keep the tenant column (D1).** Every user-facing model inherits
   `HouseholdBaseModel` (household FK + soft delete + created/updated-by-user). Don't build
   multi-household signup/billing/isolation. Don't drop `household_id`.
2. **No SaaS / multi-household behaviour (D2).** Productization, if ever, is self-hosted.
3. **API-first (D3).** All clients talk to `/api/v1/`. Business logic in the backend.
4. **No durable event bus (D4).** Node decoupling uses Django signals behind the thin
   `apps/events/` interface. **No `event_bus_events` table, no broker.** Nodes never import each
   other's models.
5. **No Celery/Redis yet (D5).** Scheduled work runs via a Django management command on cron.
   Add Redis/Celery only when a feature genuinely needs background processing.
6. **Session auth, avatar + PIN (D6).** No token auth until native apps exist. Sensitive re-auth
   uses a **password**, not the PIN. PIN + password hashed with **Argon2id**.
7. **Calendar has one source of truth (D7).** Node records own their dates. The `scheduling`
   helper creates/updates/deletes `calendar_events` and writes `calendar_event_id` back. **Nodes
   never write calendar rows directly.**
8. **One recurrence format (D8):** `recurrence_rule` (RRULE) on the owning record. No parallel
   `repeat_rule`.
9. **Search via Postgres FTS (D9)** in selectors. No hand-maintained `search_index` table.
10. **Central permission resolution (D10).** One resolver + one visibility queryset mixin. **No
    ad-hoc permission checks in views. Permission tests are written FIRST.**
11. **Attachments: `visibility` + `sensitivity` only (D11).** No per-row ACL table in V1.
12. **People vs. Users (D12):** `created_by`/`updated_by`/ownership/audit = **user**;
    `assigned_to`/subject = **person**. People may have no login.
13. **Meridian early, Solace after security (D13).** Both are **native nodes**, not external
    integrations. **No iframe / external-link layer. No `integrations` app.**
14. **Migrate Meridian/Solace by rebuild-shell + reuse-logic + import-data (D14).** Rebuild
    models/serializers/views on shared services; reuse their proven business logic; one-time
    dry-runnable import script in `scripts/`.
15. **No household specifics in schema or logic (D15).** No "two cats", no hardcoded names. Keep
    everything general for a future buyer.
16. **Calendar app is named `scheduling` (D16)**, not `calendar` (avoids stdlib clash).
17. **Backups define a working restore (D17).** Restore is tested, documented, admin-re-auth
    gated.
18. **Walking skeleton first (D18).** Build the Milestone 1 vertical slice before any other node.

### Per-app layering (Coding Standards §6)
Views are **thin** → delegate to `services` (writes) and `selectors` (reads). Every app:
`models, serializers, views, urls, permissions, services, selectors, events, tasks, tests`.

## 4. Tech stack

Backend: Python · Django · DRF · PostgreSQL. Frontend: React · TypeScript · Vite · TailwindCSS.
Deploy: Docker Compose on a Linux home server, local-network only (HTTPS/reverse-proxy/VPN
before any remote access). Redis/Celery and the mobile/desktop tech choice are deferred.

## 5. Current status

**Phase: Meridian parity/cockpit revisit in progress before Milestone 3.**

> **Deploy gotcha (read this):** the home server runs **Docker** (not Podman). After every
> `git pull` + rebuild, run **`docker exec homestack-backend python manage.py migrate`** — the
> running Postgres schema is separate from the image. Forgetting it causes `column ... does not
> exist` 500s (this bit us on the Hub page after `atlas.0002` added `quantity`/`due_at`).

- [x] Documentation consolidated to one canonical set (docs 00–22 + Milestone 1/2 checklists).
- [x] All architectural decisions made (D1–D20).
- [x] **Milestone 1 (Walking Skeleton) — DONE** (Phases 1.0–1.12). Only outstanding item:
  deploy to the home server for daily use (running via Podman locally).
- [~] **Milestone 2: native Meridian — functional, now under parity/cockpit revisit (owner
  request, 2026-07-10).** Backend + web/kiosk frontend had been marked complete: points-ledger
  parity (reservation/refund, balance vs lifetime earned), tasks (hot/behaviours/scope), routines
  + streaks, rewards shop (stock/limits/cart), group goals, wishlist, cross-node achievements
  (`apps/achievements`), notifications, scheduled command (allowance/perfect-month), settings,
  reports/leaderboard, and a dry-runnable full data importer. New product decision: **HomeStack is
  the Meridian source of truth and adult/admin cockpit; the native Meridian app is the behavioural/
  visual reference and may remain/adapt as the child-facing client.** Current shipped revisit work:
  `MeridianTaskCompletion` model/API (per-person submissions, shared/household task blocking,
  review notes/history) + adult Overview tab + task-management tab.
- [x] **Milestone 2.5: Core surfaces — Hub, Atlas, Calendar. DONE.** Full detail
  in `MILESTONE_2.5_Checklist.md` + the Progress Log below. Status by workstream:
  - **(A) Hub — DONE.** Web renders Meridian widgets; widget-config API (`/hub/widgets/…`,
    `hub.edit` perm) + "Customise" UI (household enable/order/size, per-user hide/reorder);
    "every node ships its widget" pattern; ambient **clock** widget; size-aware grid.
  - **(B) Atlas — DONE.** Postgres FTS w/ SQLite fallback (`_search`) + fixed a search visibility
    leak; unified `/atlas/search/`; item `due_at`+`quantity`; web error banner, due badges,
    quantity, search box. *(Tags/categories + templates parked; kiosk ticking blocked for kids by
    D10, by design; adult-facing kiosk ticking parked.)*
  - **(C) Calendar — DONE.** Query API window + node/person filters; month/week/day/agenda views,
    per-person colour + legend, nav; every-page `CalendarPeek` + quick-add; prefs (view/week-start/
    12-24h in localStorage); event create/edit/delete modal; `calendar_upcoming` Hub widget;
    kiosk calendar with month/week/day/agenda; dated Atlas/Hub items deep-link to Calendar day.
    *(RRULE expansion deferred D8; household-default prefs parked.)*
  - **(D) UX fixes — DONE** (kiosk enter/exit, admin-only price, keyboard PIN, login tiles, emoji
    avatars, kiosk restyle + light/dark toggle). D.6 used the legacy reference at
    `/home/moose/Documents/project-meridian`; the handover's older
    `~/Documents/new/project-meridian` path did not exist.
- [ ] Milestone 3: Home Wiki, Pets, Education. **Paused until the Meridian adult cockpit/parity
  revisit reaches a usable stopping point.** New rule from M2.5 A.3: each node must ship its
  Hub widget(s) as part of "done"** — already added to each M3 node spec.
- [ ] Milestone 4: security maturation.
- [ ] Milestone 5: native Solace.
- [ ] Milestone 6: Inventory, Assets, Hearth, Travel, Projects, Health.

## 6. Active task — Meridian parity/cockpit revisit

**Tracking doc:** `04_Development_Roadmap.md` Milestone 2 revisit note +
`MILESTONE_2_Checklist.md` Phase 2.9b / Phase 2.19 revisit notes. Reference app:
`/home/instructor/Documents/new/project-meridian`.

**Immediate next concrete step:** continue reshaping Meridian as an adult/admin cockpit over
HomeStack as source of truth. Behaviour parity first, then UI polish. Shipped so far:
`MeridianTaskCompletion` model/API, Overview approval/monitoring tab, adult task-management tab,
and adult Shop/Rewards management (reward setup, stock, visibility/archive, approvals, monitoring).
Reports/history now includes completion history and ledger panels. Next recommended slice:
**settings/admin polish** (category management, reward-category linking, allowance config UI).

**Working rhythm (proven this milestone):** small workstream → backend (models/migration/services/
selectors/serializers/views/urls) → tests → frontend (types/client → UI) → `tsc` + `npm run build`
+ `python manage.py test` (SQLite) → tick checklist → Progress Log row → commit + push to `main`.
Backend tests run on SQLite; prod/dev is Postgres — guard Postgres-only features (see Atlas
`_search`).

## 7. Guardrails — common ways to get this wrong

- Don't add Redis/Celery/event-bus tables "to be safe" — they're deliberately deferred.
- Don't put permission checks in views — use the resolver/mixin.
- Don't let a node write a `calendar_event` directly — call the scheduling helper.
- Don't import one node app's models into another — communicate via signals.
- Don't add a second auth system for Meridian/Solace — they use shared Users/People.
- Don't hardcode anything specific to this household.
- Don't skip permission tests — they come first.
- **Don't forget `migrate` after a deploy** — `docker exec homestack-backend python manage.py
  migrate` after every pull+rebuild, or you get `column ... does not exist` 500s.
- Don't use Postgres-only ORM features without a SQLite fallback — tests run on SQLite (e.g. Atlas
  `_search` branches on `connection.vendor`).

## 8. Open questions / decisions still pending

*(Append here when something needs the owner's call. None blocking Milestone 1 currently.)*

- Mobile/desktop client tech (React Native vs. Tauri vs. PWA) — deferred until after core
  product proves itself (D3). PWA is the likely first bridge.
- **Revisit Atlas + Hub after Meridian (owner request, 2026-06-25).** *Resolved → folded into the
  new **Milestone 2.5** (Core surfaces: Hub, Atlas, Calendar) in `04_Development_Roadmap.md` and §5
  above.* Both surfaces "are not functioning as I would like yet"; the milestone now scopes a
  dedicated pass on the Hub (incl. building the Meridian Hub widget + the per-node widget pattern),
  Atlas, and building out the Calendar core. Gather any remaining UX specifics from the owner when
  starting each workstream.

## 9. Progress Log

> **Append a dated entry at the end of every session.** Newest at the bottom. Keep it factual:
> what you built, what you changed, what's half-done, what the next assistant should pick up.

| Date | Author (assistant/human) | Milestone | What changed | Next step |
|------|--------------------------|-----------|--------------|-----------|
| 2026-06-23 | Planning | M0 | Consolidated docs 00–22, Milestone 1 checklist, this handover. No code yet. | Start Phase 1.0 (Docker scaffold). |
| 2026-06-23 | Assistant | M1 | **Phase 1.0 done.** Repo scaffold: `backend/ frontend/ docs/ docker/ scripts/ backups/`, `.env.example`, `.gitignore`, `README.md`, `docker-compose.yml` (3 services: postgres, backend, frontend — no Redis/Celery), `docker-compose.dev.yml` (hot-reload bind mounts). Volumes `postgres_data`/`media_data`/`backup_data`. Minimal Django backend (single `config/settings.py`, health endpoint at `/` and `/api/v1/health/`). Minimal Vite React/TS frontend with `/api` dev proxy to backend. Consolidated all docs from `documents/` → `docs/`. **Stack boots & verified:** postgres healthy, backend serves health JSON, frontend HTTP 200, proxy OK. | Start Phase 1.1: real Django project — split settings `config/settings/{base,dev,prod,test}.py`, add DRF + Argon2, create empty app skeletons (`core accounts people permissions nodes hub scheduling notifications attachments audit search backups events atlas`). |
| 2026-06-23 | Assistant | M1 | **Phase 1.1 done.** DRF + argon2-cffi added to requirements. Settings split into `config/settings/{base,dev,prod,test}.py`; `DJANGO_SETTINGS_MODULE=config.settings.dev` (manage.py/wsgi/asgi setdefault + `.env`). All 14 app skeletons created under `backend/apps/` (`apps.<name>` AppConfigs) and registered in INSTALLED_APPS; calendar app is `scheduling` (D16); `events` is the thin-signal app only (D4). Argon2id confirmed as default PASSWORD_HASHERS entry. `/api/v1/health/` now phase 1.1. **Verified:** `manage.py check` → no issues; all apps load; health OK via proxy. **Deliberately deferred to Phase 1.3** (noted in `base.py`): contrib `auth`/`sessions`/`messages`/`admin` apps + session/auth middleware + `AUTH_USER_MODEL` — added *before the first migration* so the custom `accounts.User` is in place from the start. No migrations run yet. DRF default permission is `AllowAny` until the central resolver (Phase 1.5, D10). | Start Phase 1.2: `core.Household` (single row) + seed it, `HouseholdBaseModel` (household FK, soft delete, created/updated-by-user), `HouseholdManager` default manager. |
| 2026-06-23 | Assistant | M1 | **Phase 1.2 done.** `core.Household` (tenant anchor, plain model) + idempotent seed migration `0002_seed_household` (one row: "HomeStack Household"/`homestack`, generic per D15). `HouseholdBaseModel` (abstract): `household` PROTECT FK, created/updated_at, `created_by`/`updated_by` → `AUTH_USER_MODEL` (D12, nullable), `deleted_at` soft delete, `soft_delete()`/`restore()`. `HouseholdManager` (default) excludes soft-deleted + is the single household-scoping hook (D1, no-op in single-household mode); `all_objects` includes deleted. `get_active_household()` helper for services. Migrated (only `core` — still no contrib.auth tables, custom-user trap avoided). 3 core tests pass on `config.settings.test`. **Dev workflow:** run with `-f docker-compose.yml -f docker-compose.dev.yml` (bind mount + hot reload); dev override now sets `user: ${UID:-1000}:${GID:-1000}` so container-generated files (migrations) are host-owned. Soft-delete/manager concrete test deferred to 1.3 (needs first real subclass `accounts.User`). | Start Phase 1.3: add contrib `auth`/`sessions`/`messages` + session/auth middleware, define custom `accounts.User` (on HouseholdBaseModel) and set `AUTH_USER_MODEL` **before migrating**; session auth endpoints (`pin-login`, `password-login`, `logout`, `me`, `reauth` stub); Argon2 PIN+password. |
| 2026-06-23 | Assistant | M1 | **Phase 1.3 done.** Added `django.contrib.auth/contenttypes/sessions/messages/admin` + middleware to `base.py`; set `AUTH_USER_MODEL = 'accounts.User'`. Custom `accounts.User` (AbstractBaseUser + HouseholdBaseModel): fields `display_name, username, email, avatar, pin_hash, role, is_active, is_child_account, colour` + inherited `password, last_login, household, created/updated_at, created/updated_by, deleted_at`. `UserManager` extends `HouseholdManager` (soft-delete + household scoping). Two auth backends: `PinBackend` (all users via PIN), `PasswordBackend` (non-child users via full password). Services: `pin_login_user`, `password_login_user`, `logout_user`, `reauth_user` (short-lived elevated session flag `_homestack_reauth`). Endpoints live at `/api/v1/auth/{pin-login,password-login,logout,me,reauth}/`. Django admin registered (no PermissionsMixin — custom resolver Phase 1.5). Test settings updated to use SQLite in-memory. **36/36 tests green** (core 3, accounts model 20, accounts auth 13). Soft-delete tests now covered via User. | Start Phase 1.4: `people.Person` model (linked_user_id nullable, display_name, preferred_name, avatar, colour, DOB, profile_type ∈ {adult,child,other}, notes + base fields) + CRUD endpoints at `/api/v1/people/`. |
| 2026-06-24 | Assistant | M1 | **Phase 1.4 done.** `people.Person` (HouseholdBaseModel): `linked_user` (nullable OneToOneField → User), `display_name, preferred_name, avatar, colour, date_of_birth, profile_type ∈ {adult,child,other}, notes`. Full layered app: `models, serializers (PersonSerializer + PersonWriteSerializer), selectors (list_people, get_person_by_id), services (create_person, update_person, delete_person), views (PersonListView, PersonDetailView), urls`. `PersonWriteSerializer` validates blank `display_name`. All writes stamp `created_by`/`updated_by` (D12). Delete is soft (HouseholdManager hides it from the default queryset). `python manage.py seed_people` creates 4 generic placeholder people (2 adults, 2 children — D15). Migration `people.0001_initial` generated. **68/68 tests green** (+32: 16 model, 16 view). Health endpoint bumped to phase 1.4. | Start Phase 1.5: permission resolver — write permission tests first (D10), then `permissions` models (roles, role_permissions, user_permissions), resolver function, visibility queryset mixin, wire into DRF base permission class + base selector. |
| 2026-06-24 | Assistant | M1 | **Phase 1.6 done.** `nodes` app: `Node` (global catalogue, 12 nodes seeded), `HouseholdNode` (per-household enable/display state), `NodeSetting` (per-household key-value). Data migration `nodes.0002_seed_nodes` seeds all 12 nodes + household_nodes (atlas enabled, rest disabled). Endpoints: `GET /nodes/` (nodes.view), `POST /nodes/{key}/enable|disable/` (nodes.edit, admin only), `PATCH /nodes/{key}/settings/` (nodes.edit). `HomeStackPermission` updated to respect `permission_action` view attribute so POST can override to "edit". `audit.AuditLog` (append-only, immutable `save()` guard): fields `user, action, target_node, target_record_type, target_record_id, ip_address, user_agent, metadata_json, created_at`. `log_audit()` helper in `audit/helpers.py`. Login success + failure wired into `accounts/services.py`. `GET /audit-logs/` (audit.view, admin only). Household endpoint: `GET/PATCH /household/` (household.view / household.edit). Permissions migration `0003` seeds nodes/household/audit permissions — admin gets all, manager/user/guest get view-only on nodes+household. **156/156 tests green** (+36). | Start Phase 1.7: scheduling/calendar — `CalendarEvent` model, `sync_event_for`/`delete_event_for` helper, `GET/POST/PATCH/DELETE /calendar/events/`, recurrence via RRULE. |
| 2026-06-24 | Assistant | M1 | **Phases 1.7–1.10 done.** Phase 1.7: `scheduling.CalendarEvent` (HouseholdBaseModel, visibility+sensitivity, source_node/source_record_type/source_record_id for node-backed events), `CalendarSyncMixin` (`scheduling/mixins.py`), `sync_event_for(record)` / `delete_event_for(record)` helper (scheduling/helpers.py) — nodes call these, never write CalendarEvent rows directly (D7). `events/bus.py` thin signal bus (D4). `GET/POST/PATCH/DELETE /api/v1/calendar/events/` (synced events reject direct writes). Permissions `scheduling.view/create/edit/delete` seeded. 20 tests. Phase 1.8: `atlas` app — `AtlasNote`, `AtlasList` (todo/grocery/checklist/shopping/general), `AtlasListItem` (completed_at/completed_by, assigned_to_person), `AtlasReminder` (CalendarSyncMixin: dated reminders auto-sync to CalendarEvent, D7). Full CRUD API at `/api/v1/atlas/`. `apply_visibility` updated (Phase 1.8b) — admin/manager see all, users see household+own-private, guests+children see household-only, children blocked from sensitive content. FTS via icontains (SQLite-safe; TODO: SearchVector in M2). `atlas/events.py` signals via bus (D4). Permissions seeded (user can create/edit, admin/manager can delete). 41 tests inc. 8 calendar-sync assertions. Phase 1.9: `hub` app — `HubWidget`, `HouseholdHubWidget`, `UserHubWidget`. Seed migration adds `atlas_todos` + `atlas_reminders` widgets (both kiosk-safe). `GET /api/v1/hub/` and `GET /api/v1/hub/kiosk/` (kiosk filters supports_kiosk=True). `GET /api/v1/auth/kiosk-users/` (AllowAny — returns persons-with-linked-user for kiosk avatar selection). 15 tests. Phase 1.10: kiosk frontend — installed `tailwindcss@3` + `react-router-dom`. `/kiosk` route in `App.tsx`. State machine in `KioskApp.tsx`: ambient → avatar_select → pin_entry → dashboard → (5-min idle timeout) → avatar_select. Components: `AmbientScreen` (clock), `AvatarSelect` (fetches kiosk-users, renders avatar cards), `PINEntry` (6-digit numeric pad, calls /auth/pin-login/), `KioskDashboard` (fetches /hub/kiosk/, renders todos+reminders widgets, sign-out button, inactivity timeout). API client in `src/api/client.ts`. TypeScript clean, Vite build passes. **232/232 tests green.** | Start Phase 1.11 (Backups + restore) — pg_dump + media tarball, admin re-auth gate, `POST /api/v1/backups/`, restore endpoint + documented procedure. |
| 2026-06-24 | Assistant | M1 | **Phase 1.12 done.** Web frontend. Shared primitives: `Button`, `Card`, `Avatar`, `PINPad` in `src/components/`. `AuthContext` + `LoginPage` (username → PIN flow, `me()` on load). `useDarkMode` hook (localStorage + prefers-color-scheme, class strategy). `AppShell`: sidebar nav on md+, bottom nav on mobile, dark mode toggle, user avatar + sign-out. Pages: `HubPage` (greeting, date, todo/reminder widgets with due-date badges), `AtlasPage` (tabs: Lists/Reminders; live tick-off, add/delete items and lists, reminder CRUD with datetime), `CalendarPage` (upcoming events grouped by date, today/tomorrow labels). API client extended with all Atlas/Calendar/Hub/auth endpoints. TypeScript clean. Podman dev stack running and verified locally (kiosk + web both work). | Deploy to home server (start Milestone 2: native Meridian) when ready to go daily. |
| 2026-06-24 | Assistant | M1 | **Phase 1.11 done.** Backups + restore (D17). `apps/backups`: `Backup` model (status/label/db_file/media_file/db_checksum/media_checksum/size_bytes/error_message), `services.create_backup` (pg_dump + media tar, checksum, audit log), `services.restore_backup` (checksum verify, pg_restore, unpack media, audit log). Low-level ops (`_dump_db`, `_tar_media`, `_restore_db`, `_unpack_media`) isolated so tests patch them without needing a real PG. `POST /api/v1/backups/` (admin+reauth), `GET /api/v1/backups/`, `GET /api/v1/backups/{id}/download/` (streaming tar.gz), `POST /api/v1/backups/{id}/restore/` (admin+reauth). Permissions seeded: `backups.view/create/restore` — admin only. `docs/restore.md`: full step-by-step restore procedure (API path + manual fallback). **248/248 tests green** (+16 backup tests). `BACKUP_DIR`/`MEDIA_ROOT` added to `base.py`. | Start Phase 1.12: web frontend — shared component primitives, auth flow (avatar+PIN), Hub view, Atlas UI (lists/items/reminders), Calendar view, dark mode + large touch targets. |
| 2026-06-25 | Assistant | M4-pull-fwd | **User management (admin) — pulled forward from M4.** New `users` permission (admin-only, perms migration 0012). Backend: `accounts/user_services.py` (create/update/deactivate + person link/create), `user_views.py` + `/api/v1/users/` (`user_urls.py`), `UserAdminSerializer`/`UserWriteSerializer`, `list_users` selector. Create links an existing unlinked Person or auto-creates one (owner's choice). Frontend: admin **Users** page (`features/web/pages/UsersPage.tsx`) — list, create (username/role/PIN/password/child/colour + person link), inline edit (role, reset PIN/password), deactivate; admin-only nav entry + `/users` route. Can't deactivate self. **350 tests green** (+11); frontend builds clean. | Continue M2 polish / M3, and the Atlas+Hub follow-up (§8). |
| 2026-06-25 | Assistant | M2 | **Frontend full set (2.19) — M2 COMPLETE.** Rebuilt the Meridian web UI to match the legacy templates (per-feature components under `frontend/src/features/web/pages/meridian/`): Tasks board (filters, badges, base+bonus, role-aware actions, create form), Shop (cart + checkout, stock, admin create + approvals), Routines (streaks), Goals + Wishlist (progress + contribute + request/approve/fulfill), Leaderboard + Badges, admin Settings; plus a notification bell in `AppShell`. Kiosk: tap-to-complete tasks & routines (celebration), reward shop, goals/wishlist quick-contribute, my-badges strip. API client + types extended for every endpoint; added `getPeople`, `updateMeridianTask/Reward`. `tsc` + production build clean. Backend untouched (339 tests still green). | **Milestone 3** (Home Wiki, Pets, Education) — but first revisit Atlas + Hub UX (owner request, §8). Optionally tackle carried-forward polish (2.9b, etc.). |
| 2026-06-25 | Assistant | M2 | **Full data import (2.18).** Extended `import_meridian` (dry-runnable) to the whole feature set: categories(kind), point-ledger with `transaction_type` (so balance AND lifetime-earned match), routines+completions, group goals+contributions, wishlist items/contributions/requests, earned badges, allowances. Entities idempotent (natural keys); history append-only (run once / after wipe). **339 tests green.** | Last phase: 2.19 frontend (web + kiosk) for the full feature set; then 2.9b. |
| 2026-06-25 | Assistant | M2 | **Settings + reports + category kinds (2.17).** `apps/meridian/config.py` — typed household settings over `NodeSetting` (`points_label`, `group_goals_enabled`, `wishlist_requests_enabled`, `auto_end_streaks`); `GET/PATCH /meridian/settings/` (PATCH=manager via `get_permission_action`). Toggles enforced in `contribute_to_goal`/`request_wishlist_item`; `current_streak` now defaults to the `auto_end_streaks` setting (default False = lenient, legacy parity). `MeridianCategory.kind` (task/reward, migration 0010) + `?kind=` filter. `GET /meridian/reports/` leaderboard (balance/earned/badges) + recent activity. **337 tests green.** | Continue: 2.18 full data import, 2.19 frontend; 2.9b. |
| 2026-06-25 | Assistant | M2 | **Atlas blank-screen fix + scheduled command (2.16).** Fixed `GET /atlas/lists/` using the write serializer (no `id`/`items`) → web ListCard crashed once a list existed; now uses the read serializer + frontend defaults items to []; regression test added. Phase 2.16: `meridian_run_scheduled` management command (D5 cron) — `MeridianAllowance` (per-person weekly allowance, migration 0009) + `award_allowances` (idempotent per day, notifies), perfect-month routine badge via `award_perfect_month_badges` → `meridian.routine_perfect_month` event → achievements awards. Streak auto-end is read-time (no job); recurring-task re-arm deferred to 2.9b; allowance config UI → 2.17/2.19. **330 tests green.** | Continue: 2.17 settings/reports/leaderboard, 2.18 import, 2.19 frontend; 2.9b. |
| 2026-06-25 | Assistant | M2 | **Notifications (2.15).** Built the scaffolded `notifications` app as shared infra (called directly by nodes, like audit/scheduling): `Notification` model, `create_notification`/`notify_person[_id]`/`mark_read`/`mark_all_read`, `GET /notifications/` (+unread_count), read + read-all endpoints, `notifications.view` perm (migration 0011), `notifications.0001_initial`. Wired into Meridian (task approved/rejected, reward approved/rejected) and achievements (badge earned) via direct service calls. Allowance notification comes with 2.16; bell/list UI with 2.19. **324 tests green.** | Continue: 2.16 scheduled cmd, 2.17 settings/reports, 2.18 import, 2.19 frontend; 2.9b. |
| 2026-06-25 | Assistant | M2 | **Deploy fixes + cross-node achievements (2.14).** Fixed two LAN-deploy traps surfaced by live testing: (1) `CSRF_TRUSTED_ORIGINS` now read from env + auto-derived from `DJANGO_ALLOWED_HOSTS` in dev (Django 4 Origin check rejected the SPA's `:5173` origin behind the Vite `changeOrigin` proxy); (2) documented in README that the base compose bakes source at build time so a rebuild (or the dev-override bind mount) is required after `git pull`. Phase 2.14: new `apps/achievements` (cross-node, D20) — `Badge` (global catalogue, 15 seeded), `PersonBadge`, `AchievementCounter`; awards purely via the events bus in `handlers.connect()` (no Meridian imports, D4). Enriched Meridian events (routine `streak`, points `transaction_type`, `wishlist_contributed`). `achievements.view` perm (migration 0010). **316 tests green.** `perfect_month` → 2.16; badge UI → 2.19. | Continue: 2.15 notifications, 2.16 scheduled cmd, 2.17 settings/reports, 2.18 import, 2.19 frontend; 2.9b task-completion model. |
| 2026-06-25 | Assistant | M2 | **Meridian economy ported (phases 2.10/2.12/2.13).** 2.10 rewards shop: stock (`remaining_stock`/`disappear_when_empty`), `daily_limit_per_user`, `allow_multiple_in_cart`, price/store/image fields, archive, `checkout_cart` (all-or-nothing); uploaded image carousel deferred to attachments. 2.12 group goals: `MeridianGroupGoal` + contribution (reserve/refund, funded), child-safe `contribute`. 2.13 wishlist: request→approve→item→contribution (reserve/refund, funded/fulfilled), child-safe request+contribute. Added `meridian.contribute` permission (perms migration 0009) + resolver carve-out; `HomeStackPermission` now supports `get_permission_action(request)` for mixed-method views. Migrations meridian 0006–0008. **307 tests green.** Not committed in this row (committed next). | Continue strict order: 2.14 achievements app (cross-node, D20), 2.15 notifications, 2.16 scheduled cmd, 2.17 settings/reports, 2.18 import, 2.19 frontend; plus 2.9b task-completion model. |
| 2026-06-25 | Assistant | M2 | **Meridian full-port build started (D19/D20 ratified into changelog).** Phase 2.8 ledger parity: typed signed transactions (`MeridianPointsEntry.TransactionType`), `get_total_earned` (earning types only) vs `get_points_balance`, reward **reservation/refund** (reserve on request, idempotent refund on reject/cancel, no double-deduct on approve). Phase 2.9 tasks parity (additive): `completion_behavior`, `is_active`/`is_archived`, hot `hot_bonus_points`/`hot_label` + `award_value`, `completion_scope`/`availability_window` fields; **deferred** per-person completion history / shared & recurring completion / evidence / admin-complete-for-person to a `MeridianTaskCompletion` model (Phase 2.9b). Phase 2.11 routines+streaks: `MeridianRoutine` + `MeridianRoutineCompletion`, immediate points (no approval), idempotent per day, streak calc, admin void claws back; full API + child-safe complete. Migrations 0003–0005. **292 tests green** (+10). Not committed. | Continue: Phase 2.10 rewards shop (stock/limits/images/cart), then 2.12 goals, 2.13 wishlist, 2.14 achievements app, 2.15 notifications, 2.16 scheduled cmd, 2.17 settings/reports, 2.18 import, 2.19 frontend. |
| 2026-06-25 | Assistant | M2 | **Audit + scope correction + bug fix.** Found the Progress Log was missing all M2 + design-system/seed-admin/prod-cookie commits, and §5 was stale ("code not started"). **Fixed a CSRF write bug breaking ALL browser writes** (Atlas save, Meridian add, every POST/PATCH/DELETE): DRF `SessionAuthentication` enforces CSRF but the SPA never sent a token. Fix: `@ensure_csrf_cookie` on `GET /auth/me/` (`accounts/views.py`) + client reads `csrftoken` cookie → `X-CSRFToken` header on unsafe methods (`api/client.ts`). **Audited native Meridian vs the legacy app** (`~/Documents/new/project-meridian`, 20 models/9 services): only a thin tasks/points/rewards subset was ported — no routines/streaks, group goals, wishlist, badges, allowance, shop depth (stock/limits/images/cart), reports/leaderboard, notifications, or separate task/reward categories. **Rewrote `15_Node_Meridian.md` and `MILESTONE_2_Checklist.md`** to the true full-port scope (Parts A/B/C). Proposed **D19** (Meridian = full port) and **D20** (cross-node achievements/badges system) — ratify into `00_README_and_Changelog.md` on sign-off. | **Owner sign-off on the rewritten M2 spec**, then build Part B (wire up foundation) → Part C phases 2.8–2.19. |
| 2026-06-24 | Assistant | M1 | **Phase 1.5 done.** Permission spine (D10) fully implemented. `permissions` app: `Permission` (global catalogue, `{resource}.{action}` codenames), `Role` (HouseholdBaseModel, system roles: admin/manager/user/guest), `RolePermission` (join: role→permission), `UserPermission` (HouseholdBaseModel, per-user override with `is_granted`). Data migration `0002_seed_roles_and_permissions` seeds 4 system roles + 4 `people.*` permissions + default matrix (admin/manager=all, user/guest=view-only). **Resolver** (`permissions/resolver.py`): unauthenticated/inactive→deny; `is_child_account+non-view`→deny; user_permission override first; role_permission fallback. **Visibility mixin** (`permissions/visibility.py`): structural passthrough, ready to extend in Phase 1.8 when Atlas adds visibility/sensitivity. **DRF class** (`permissions/drf.py`): `HomeStackPermission.for_resource("people")` factory — no view checks permissions ad hoc. `people/views.py` switched from `IsAuthenticated` to `HomeStackPermission`. `people/selectors.py` now passes user to `apply_visibility`. **120/120 tests green** (+52: 31 resolver, 21 integration). | Start Phase 1.6: nodes registry (`nodes`, `household_nodes`, `node_settings`), seed node rows (atlas enabled), minimal household settings endpoints, audit log. |

| 2026-06-25 | Assistant | M2.5 | **M2.5 kicked off (Core surfaces).** Added core-service specs `23_Core_Hub.md` + `24_Core_Calendar.md` (Hub = read-only widget aggregation; Calendar = `scheduling`, D7 timeline, every-page access + configurable + nice-to-look-at per owner). Inserted **Milestone 2.5 — Core surfaces (Hub/Atlas/Calendar)** in `04_Development_Roadmap.md` (before M3) + `MILESTONE_2.5_Checklist.md`; updated §5 status + resolved the §8 Atlas/Hub open question into it. Parked an Obsidian-style **node graph "web" view** in `10_Future_Features_Parking_Lot.md` §4. **First build:** found Meridian Hub widgets were already seeded (mig `0003`) + content-wired in `hub/services.py`, and the **kiosk** already rendered them, but the **web `HubPage`** only rendered the two Atlas widgets (Meridian fell through to the reminders renderer). Fixed: web HubPage now renders Meridian tasks/points/reward-requests via a key dispatcher (`tsc` + production build clean). | Continue M2.5: **2.5A.1** widget-config endpoints (household enable/order/size + per-user reorder) → **2.5A.2** Hub config UI; then Atlas FTS (**2.5B.1**) and the Calendar core build (**2.5C**). Smoke-test the web Meridian widgets live on the home server. |

| 2026-06-25 | Assistant | M2.5 | **UI/UX fixes (Workstream D) noted + 3 of 6 shipped.** Logged six owner UX items as Phases 2.5D.1–.6 in the checklist. Done: **(D.1)** enter/exit kiosk buttons (web shell `→ /kiosk`; kiosk ambient corner link `→ /`); **(D.2)** estimated cost (`price_estimate`) is now **admin-only** in shop/wishlist/group-goals — `AdminOnlyPriceMixin` (fails closed) + `request` context threaded through all Meridian output call sites, with tests (74 meridian tests green); **(D.3)** hardware-keyboard PIN entry on web `PINPad` + kiosk `PINEntry`. `tsc` + build clean. | **Remaining D items:** D.4 user-tiles web login (reuse kiosk-users; confirm all login users have a linked Person), D.5 emoji account pictures (store in `User.avatar`, `Avatar` emoji→img→initials, picker on Users page), D.6 kiosk restyle to match **original Meridian** (need legacy ref `~/Documents/new/project-meridian`) + kiosk light/dark toggle. Then resume A.1 widget-config API / C Calendar core. |

| 2026-06-25 | Assistant | M2.5 | **UX fixes D.4 + D.5 shipped.** **(D.5) Emoji account pictures:** stored in `User.avatar`; `Avatar` renders emoji→image→initials (`isImageAvatar` helper); emoji picker (preset grid) on the admin Users create/edit forms + avatar shown in user rows; `kiosk-users` now returns the account avatar (`User.avatar` ?? `Person.avatar`) so emoji show on web login tiles, kiosk avatar-select + PIN. **(D.4) Web login user tiles:** `LoginPage` shows avatar tiles (from `getKioskUsers`) → PIN, with a "username instead" fallback so no one is locked out. **352 backend tests green; tsc + build clean.** Committed + pushed. | **Remaining D item:** D.6 kiosk restyle to match original Meridian (needs legacy ref `~/Documents/new/project-meridian`) + kiosk light/dark toggle. Then **Workstream 2.5A** in full: A.1 widget-config endpoints (household enable/order/size + per-user reorder) → A.2 Hub config UI → A.4 usability polish (A.3 Meridian widget already done). |

| 2026-06-25 | Assistant | M2.5 | **Workstream A (Hub) complete (A.1/A.2/A.4; A.3 already done).** **A.1 widget-config API:** `GET /hub/widgets/` (catalogue + household + per-user state via `hub/selectors.list_widget_config`), `PATCH /hub/widgets/<key>/` (household enable/order/size, new `hub.edit` perm migration `0013`, admin/manager), `PATCH /hub/widgets/<key>/me/` (per-user hide/reorder, self via `permission_action="view"`); `get_hub_widgets` now scopes to `user.household` + applies per-user reorder/hide; +5 hub tests (20 green). **A.2 config UI:** `HubConfig` panel ("⚙ Customise" on the Hub) — per-user show/hide + up/down reorder; admin household enable/disable + size; refreshes live. **A.4 polish:** size-aware responsive grid, clearer empty-state, ambient **clock** widget (`source_node=null`, kiosk-safe, hub migration `0004`, rendered client-side web+kiosk). **357 backend tests green; tsc + build clean.** Committed + pushed. | **A.4 leftover:** wire Calendar "upcoming" widget (needs Workstream C). Then **D.6** (kiosk restyle to original Meridian — needs `~/Documents/new/project-meridian` ref + kiosk light/dark), and **Workstream B** (Atlas FTS + UX) / **C** (Calendar core). |

| 2026-06-25 | Assistant | M2.5 | **Workstream B (Atlas) complete.** **B.1 FTS:** `atlas/selectors._search` uses Postgres `SearchVector`/`SearchQuery` in prod, `icontains` fallback on SQLite (tests); applied to notes/lists/items/reminders. **Fixed a visibility leak** in `search_atlas` (lists/reminders now permission-filtered; item hits restricted to visible lists). New `GET /atlas/search/?q=`. **B.2 fields:** `AtlasListItem` gained `due_at` + `quantity` (migration `0002`) + `atlas_list_id` in serializer; services allow-list updated. **B.3 UX:** web Atlas error banner, item due-date badges + quantity prefix, debounced Atlas-wide search box. Kiosk Atlas ticking intentionally **not** added — children can't complete items (resolver blocks child non-view actions, D10). +6 atlas tests (47). **362 backend tests green; tsc + build clean.** Committed + pushed. | **Remaining M2.5:** D.6 (kiosk restyle to original Meridian — needs `~/Documents/new/project-meridian` + kiosk light/dark), A.4 Calendar "upcoming" widget, and **Workstream C — Calendar core** (the big one: month/week/day/agenda, every-page access, configurable). Tags/categories + templates for Atlas remain parked. |

| 2026-06-25 | Assistant | M2.5 | **Workstream C (Calendar core) complete.** **C.1:** `GET /calendar/events/` now takes `start`/`end` window + `node`/`person` filters (permission-filtered, D10); serializer exposes `source_node` key; synced events stay read-only (D7). **C.2:** new `CalendarPage` — month grid / week / day / agenda views, prev-today-next nav, per-person colour coding + legend, today marker. **C.3:** `CalendarPeek` popover in the shell header on every page (next events + quick-add + open-calendar). **C.4:** saved default view + start-of-week + 12/24h (localStorage); source/person filters. **C.5:** event create/edit/delete modal; synced events read-only with "edit in node" note; RRULE expansion deferred (D8). **C.6 / A.4 leftover:** `calendar_upcoming` Hub widget (migration `0005`, web + kiosk). Fixed a latent frontend bug (type used `all_day`/`source_node` vs API `is_all_day`). +4 scheduling tests. **365 backend tests green; tsc + build clean.** Committed + pushed. | **M2.5 nearly done.** Remaining: **D.6** kiosk restyle to original Meridian (needs `~/Documents/new/project-meridian` ref + kiosk light/dark). Optional follow-ups: calendar household-default prefs, RRULE expansion, deep-links from node items, Atlas tags/categories. |

| 2026-06-25 | Assistant | M2.5 | **D.6 kiosk look & feel complete.** The expected legacy path `~/Documents/new/project-meridian` was missing, so used `/home/moose/Documents/project-meridian` (`app/static/css/homestack.css`, kiosk templates) as the reference. Restyled React kiosk screens (`AmbientScreen`, `AvatarSelect`, `PINEntry`, `KioskDashboard`) from hardcoded gray/dark styling to shared HomeStack tokens: warm paper background, raised cards, primary/warning/success accents, larger child-friendly cards/buttons. Added kiosk light/dark toggle via `KioskThemeToggle` using shared `hs-dark` preference. Fixed dashboard header emoji avatars by distinguishing emoji from image URLs. `npm run build` clean; `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test` green (365 tests). | Start **2.5X verification**: role/permission smoke checks across Hub/Atlas/Calendar, then home-server run-through/deploy. |

| 2026-06-25 | Assistant | M2.5 | **2.5X kiosk follow-ups shipped.** Improved kiosk light-theme contrast by moving kiosk screens to the stronger `sunken` background and using `raised` panels with stronger borders/shadows. Added a direct kiosk Calendar surface in `KioskDashboard`: Home/Calendar switch, month/week/day/agenda modes, event cards with time/source/location, using the existing permission-filtered `/calendar/events/` API. Added a kiosk dashboard "Web mode" link back to `/`. `npm run build` clean. | Continue **2.5X verification**: Atlas reminders Hub+Calendar no double-write, Meridian Hub/Calendar role smoke checks, backend suite, home-server run-through/deploy. |

| 2026-06-25 | Assistant | M2.5 | **M2.5 closed.** Added the Hub-widget completion rule to Home Wiki/Pets/Education specs. Fixed Hub `atlas_todos` to read through a permission-filtered Atlas selector instead of direct model access. Added cross-surface tests: Atlas dated reminder appears in Hub reminders + Calendar widget with one CalendarEvent; private Atlas list items do not leak to child Hub; Atlas/Meridian synced calendar events expose source node and respect visibility. Added Atlas/Hub deep-links into Calendar day view. `npm run build` clean; full backend suite green (**369 tests**). README and handover now point to M3. | Start **Milestone 3: Home Wiki, Pets, Education**. Remember every node must ship Hub widget rows/selectors as part of done. |

| 2026-07-10 | Assistant | M2 revisit | **Meridian parity/cockpit revisit started (owner direction).** Product direction clarified: **HomeStack becomes the Meridian source of truth and adult/admin cockpit**; the native Meridian app at `/home/instructor/Documents/new/project-meridian` is the behaviour/style reference and may remain/adapt as child-facing client. Behaviour parity first: added `MeridianTaskCompletion` model + migration `0011` (submitted/approved/rejected, per-person history, review notes, evidence placeholder), completion-based service flow with backward-compatible task endpoints, completion list/approve/reject API, tests for per-person vs household/shared completions and specific-completion approval. Frontend: typed completion API bindings, new default **Meridian Overview** tab for pending task/reward approvals + balances/activity, and rebuilt **Tasks** as an adult management table with filters, inline edit, hide/archive/delete, pending completion actions, and recent completion history. **372 backend tests green; frontend `tsc && vite build` clean.** Applied migrations to local running DB. | Commit + push, then continue adult cockpit with **Shop/Rewards management** (setup, stock, approvals, monitoring) before broader UI polish. |

| 2026-07-10 | Assistant | M2 revisit | **Adult Shop/Rewards management shipped.** Rebuilt `ShopTab` from a shopper/product-card-first surface into an adult management view for admins/managers: metrics (active rewards, pending requests, out-of-stock), filters (active/needs approval/out-of-stock/hidden/all), reward table with image, stock, price/store, daily limit, multi-cart badges, inline pending request approvals, inline edit form (name, cost, description, image/store/price, stock, daily limit, multiple-cart, hide-when-empty, active), hide/show, archive/unarchive, delete, and a side pending-request queue. Non-manager shopper view remains card/cart based but secondary. Frontend `tsc && vite build` clean. | Next: reports/history polish from `MeridianTaskCompletion`, then settings/admin polish (category management, reward-category linking, allowance config UI). |

| 2026-07-10 | Assistant | M2 revisit | **Reports/history cockpit polish shipped.** `LeaderboardTab` now acts more like an adult audit surface: metrics for approved/submitted/rejected completions, ledger-entry count, badges earned; leaderboard retained; badge catalogue moved into a denser panel; added **Task completion history** (status, person, timestamps, rejection reason/review note) from `MeridianTaskCompletion`; added **Points ledger** panel from `/meridian/points/`. Frontend `tsc && vite build` clean. | Next: settings/admin polish — category management UI, reward-category linking (backend + frontend), allowance config UI. |

### Session notes (free-form, optional)

*(Use this space for anything that doesn't fit the table — gotchas, decisions made mid-session,
things you were unsure about. Date each note.)*

---

## 10. How to update this file

At the **end of your session**: (1) tick the boxes you completed in `MILESTONE_1_Checklist.md`;
(2) update **§5 Current status** if a milestone's state changed; (3) add a **Progress Log** row;
(4) if you made or hit a decision, note it in **§8**; (5) if you had to deviate from a Hard Rule,
say so explicitly in the log and explain why. Keep this file honest — it is the memory that lets
the next assistant continue without re-reading everything.
