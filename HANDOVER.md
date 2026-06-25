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
- `MILESTONE_1_Checklist.md` — the current build checklist (tick boxes as you go).

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

**Phase: Milestone 1 functionally complete; Milestone 2 in progress (foundation only).**

- [x] Documentation consolidated to one canonical set (docs 00–22 + Milestone 1/2 checklists).
- [x] All architectural decisions made (D1–D20).
- [x] **Milestone 1 (Walking Skeleton) — DONE** (Phases 1.0–1.12). Only outstanding item:
  deploy to the home server for daily use (running via Podman locally).
- [x] **Milestone 2: native Meridian — DONE (full port, D19/D20).** Backend (339 tests) + web
  & kiosk frontend complete: points-ledger parity (reservation/refund, balance vs lifetime
  earned), tasks (hot/behaviours/scope), routines + streaks, rewards shop (stock/limits/cart),
  group goals, wishlist, cross-node achievements (`apps/achievements`), notifications, scheduled
  command (allowance/perfect-month), settings, reports/leaderboard, and a dry-runnable full data
  importer. *Carried forward (non-blocking): `MeridianTaskCompletion`/2.9b (shared & recurring
  tasks + photo evidence), reward image carousel, reward→category link, `kiosk_pin_skip`, live
  kiosk badge celebration.* Run the importer to retire the standalone app.
- [ ] **Milestone 3: Home Wiki, Pets, Education. ← next.** (First, per owner request §8: revisit
  Atlas + Hub UX now that Meridian is done.)
- [ ] Milestone 4: security maturation.
- [ ] Milestone 5: native Solace.
- [ ] Milestone 6: Inventory, Assets, Hearth, Travel, Projects, Health.

## 6. Active task — Milestone 1

Build the vertical slice in `MILESTONE_1_Checklist.md`, in order:
Docker scaffold → Django + settings → Household + base model → Accounts/auth → People →
**Permissions (tests first)** → Settings/audit → Scheduling + helper → Atlas → Hub → Kiosk shell
→ Backups + restore → Frontend slice.

**Definition of done:** family logs in (web + kiosk), uses Atlas lists/reminders, sees them on
Hub and Calendar, permissions enforced and tested, backup **and restore** work, runs in Docker,
used daily.

**Suggested next concrete step if nothing exists yet:** Phase 1.0 — scaffold the repo and a
3-service `docker-compose.yml` (backend, frontend, postgres), confirm it boots.

## 7. Guardrails — common ways to get this wrong

- Don't add Redis/Celery/event-bus tables "to be safe" — they're deliberately deferred.
- Don't put permission checks in views — use the resolver/mixin.
- Don't let a node write a `calendar_event` directly — call the scheduling helper.
- Don't import one node app's models into another — communicate via signals.
- Don't add a second auth system for Meridian/Solace — they use shared Users/People.
- Don't hardcode anything specific to this household.
- Don't skip permission tests — they come first.

## 8. Open questions / decisions still pending

*(Append here when something needs the owner's call. None blocking Milestone 1 currently.)*

- Mobile/desktop client tech (React Native vs. Tauri vs. PWA) — deferred until after core
  product proves itself (D3). PWA is the likely first bridge.
- **Revisit Atlas + Hub after Meridian (owner request, 2026-06-25).** Both work but "are not
  functioning as I would like yet." Once the Meridian full port (M2) is complete, do a dedicated
  pass on Atlas and the Hub to refine behaviour/UX to the owner's expectations. Gather specifics
  from the owner at that point.

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
