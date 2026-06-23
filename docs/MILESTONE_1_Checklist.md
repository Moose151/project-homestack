# Milestone 1 — Walking Skeleton: Build Checklist

> A complete, daily-usable vertical slice: auth + People + Atlas + Hub + Calendar, in Docker,
> with permissions and tests. Build in this order. Decisions referenced as D1–D18 live in
> `00_README_and_Changelog.md`. **Permission tests are written first (D10).**
>
> Checkbox legend: `[ ]` todo · `[~]` in progress · `[x]` done.

---

## Phase 1.0 — Repo & Docker scaffold

- [x] Create repo structure (Coding Standards §2): `backend/ frontend/ docs/ docker/ scripts/ backups/`, `.env.example`, `docker-compose.yml`, `docker-compose.dev.yml`, `README.md`.
- [x] `docker-compose.yml` with **three** services only: `homestack-backend`, `homestack-frontend`, `homestack-postgres` (D5 — **no Redis/Celery yet**).
- [x] Volumes: `postgres_data`, `media_data`, `backup_data`.
- [x] `.env.example` with DB creds, Django secret, allowed hosts (local only).
- [x] Confirm stack boots: `docker compose up` serves an empty backend + frontend, Postgres healthy.

## Phase 1.1 — Django project + settings

- [x] Django + DRF installed; project at `backend/config/`.
- [x] Split settings: `settings/{base,dev,prod,test}.py`.
- [x] `urls.py`, `asgi.py`, `wsgi.py`. API base path `/api/v1/`.
- [x] Argon2 password hasher configured (D6) for PINs and passwords.
- [x] App skeletons created (empty for now): `core accounts people permissions nodes hub scheduling notifications attachments audit search backups events atlas`. (Other node apps added in later milestones.)
- [x] **Name the calendar app `scheduling`, not `calendar` (D16).**

## Phase 1.2 — Core: Household + base model (D1, D12)

- [x] `core.Household` model (single row): `name, slug, timezone, default_locale`.
- [x] Seed exactly one household row (data migration or management command). *(idempotent data migration `0002_seed_household`)*
- [x] `HouseholdBaseModel` (abstract): `household` FK, `created_at`, `updated_at`, `created_by`/`updated_by` (→ user), `deleted_at` (soft delete).
- [x] `HouseholdManager` default manager: filters to the active household **and** excludes soft-deleted rows. *(soft-delete enforced now; household scoping lives here as the single hook — structural no-op in single-household mode, D1)*
- [x] Confirm: every future model inherits this and never re-implements scoping/soft-delete.

## Phase 1.3 — Accounts + authentication (D6)

- [ ] `accounts.User`: `display_name, username, email, avatar, pin_hash, password_hash, role, is_active, is_child_account, colour, last_login_at` + base fields. `role ∈ {admin, manager, user, guest}`.
- [ ] Session-based auth (Django sessions) — **no token auth yet** (D6).
- [ ] Endpoints: `POST /auth/pin-login/`, `POST /auth/password-login/`, `POST /auth/logout/`, `GET /auth/me/`.
- [ ] `POST /auth/reauth/` (password-based) — stub that grants a short-lived elevated session flag (consumed later by sensitive nodes).
- [ ] PIN + password hashed with Argon2id. PIN never the sole gate for sensitive data.

## Phase 1.4 — People (D12)

- [ ] `people.Person`: `linked_user_id` (nullable), `display_name, preferred_name, avatar, colour, date_of_birth, profile_type ∈ {adult,child,other}, notes` + base fields.
- [ ] CRUD endpoints `/api/v1/people/`.
- [ ] **Rule wired in:** ownership/audit (`created_by/updated_by`) = user; subjects/assignees = person.
- [ ] Seed the household's real people (2 adults, 2 children) as a dev convenience (not hardcoded in app logic — D15).

## Phase 1.5 — Permissions: the security spine (D10) — TESTS FIRST

- [ ] **Write permission tests before the resolver** (D10, Coding Standards §10).
- [ ] `permissions` models: `roles, permissions, role_permissions, user_permissions` (per-user overrides).
- [ ] **Permission resolver** — one function: `(user, action, resource/node) → allow/deny`, combining role + per-user overrides + node-enabled + visibility + sensitivity + re-auth state.
- [ ] **Visibility queryset mixin** — applied in selectors so list endpoints return only permitted rows (household, role, visibility, sensitivity, re-auth).
- [ ] Wire both into DRF (a base permission class + a base selector) so **no view checks permissions ad hoc**.
- [ ] Tests green: admin/manager/user/child see exactly what they should across a sample model.

## Phase 1.6 — Settings shell + Audit

- [ ] `nodes` registry: `nodes, household_nodes, node_settings`. Seed node rows (atlas enabled; others disabled).
- [ ] `GET /api/v1/nodes/`, enable/disable, `PATCH .../settings/`.
- [ ] `audit.AuditLog` + helper; log logins, failed logins, node enable/disable, backup actions (extend later).
- [ ] Minimal Settings endpoints (`GET/PATCH /household/`).

## Phase 1.7 — Scheduling (Calendar) + helper (D7, D8)

- [ ] `scheduling.CalendarEvent`: fields per DDD §6, incl. `source_node_id/source_record_type/source_record_id`, `visibility`, `sensitivity`, `recurrence_rule`, `assigned_to_person_id`, `calendar_event` linkage.
- [ ] **The scheduling helper**: `sync_event_for(record)` / `delete_event_for(record)` — creates/updates/deletes a `CalendarEvent` from any node record and writes `calendar_event_id` back. Nodes call this on save/delete and **never write calendar rows directly**.
- [ ] One recurrence representation (RRULE) on the owning record; helper expands it (D8).
- [ ] `GET/POST/PATCH/DELETE /api/v1/calendar/events/` (direct writes only for standalone events).
- [ ] Tests: creating/updating/deleting a source record keeps its event in sync.

## Phase 1.8 — Atlas (the one real node, D18)

- [ ] Models on the base model: `atlas_notes`, `atlas_lists` (`list_type`), `atlas_list_items` (`assigned_to_person_id`, `completed_by` user), `atlas_reminders` (`recurrence_rule`, `calendar_event_id`).
- [ ] App layout (Coding Standards §6): `models, serializers, views (thin), urls, permissions, services, selectors, events, tasks, tests`.
- [ ] CRUD per API spec §10; list endpoints use the visibility mixin.
- [ ] Dated reminders/items sync to the Calendar **via the scheduling helper** (not direct writes).
- [ ] FTS search in `selectors` (D9) — no manual index table.
- [ ] `events.py` publishes Atlas signals via the thin `events` interface (D4) — no cross-node model imports.
- [ ] Tests: permissions, CRUD, calendar sync, search.

## Phase 1.9 — Hub

- [ ] `hub_widgets`, `household_hub_widgets`, `user_hub_widgets`.
- [ ] `GET /api/v1/hub/` returns permission-aware widgets (Atlas to-dos, reminders due, today's checklist).
- [ ] `GET /api/v1/kiosk/hub/` returns kiosk-safe subset only.

## Phase 1.10 — Kiosk shell

- [ ] Frontend `/kiosk` mode with states: ambient → avatar selection → PIN entry → dashboard → timeout return.
- [ ] Automatic timeout returns to avatar selection; clear logout control.
- [ ] No sensitive widgets on kiosk Hub by default (none exist yet — keep it that way).

## Phase 1.11 — Backups + restore (D17) — restore must actually work

- [ ] `backups` table + `POST /api/v1/backups/` (pg_dump + media tarball, checksum, status).
- [ ] `GET /backups/`, `GET /backups/{id}/download/`.
- [ ] `POST /backups/{id}/restore/` — **requires admin re-auth**.
- [ ] **Documented restore procedure** in `docs/` or `scripts/restore.md`: stop app / maintenance, `pg_restore`, unpack media, verify checksums, restart; state expected downtime.
- [ ] **Test it:** take a backup, restore into a clean DB, confirm data integrity (Coding Standards §10).

## Phase 1.12 — Frontend slice

- [ ] React/TS/Vite/Tailwind scaffold; shared component primitives (button, card, list, PIN pad, avatar).
- [ ] Auth flow (avatar + PIN) against the session API.
- [ ] Atlas UI: lists, list items (tick off), simple reminders, mobile-friendly.
- [ ] Hub view with Atlas widgets.
- [ ] Calendar view showing Atlas dated items.
- [ ] Dark mode + large touch targets baseline (UI/UX §11).

---

## Definition of done (Milestone 1)

- [ ] Family logs in on **web and kiosk** (avatar + PIN).
- [ ] Atlas lists/reminders usable; appear on **Hub and Calendar** (no double-written dates).
- [ ] Permissions **enforced and tested** through the central resolver/mixin (admin/manager/user/child correct).
- [ ] Backup **and restore** both work and are tested.
- [ ] Runs in Docker on the home server; **you use it daily.**

> When all boxes are ticked, update `HANDOVER.md` (status → Milestone 2) and start **native
> Meridian** (Roadmap M2): rebuild shell on shared services, reuse reward/points logic, import
> live data.
