# Milestone 2 — Native Meridian: Build Checklist

> Canonical for M2. Global rules from `00_README_and_Changelog.md` (D1–D18) apply.
> Source node spec: `15_Node_Meridian.md`. Roadmap: `04_Development_Roadmap.md` (Milestone 2).
> Built end-to-end on the proven Atlas pattern (models → services → selectors → serializers →
> thin views → urls → permissions → calendar helper → events → tests).

## Phase 2.0 — App + models (D1, D13, D14)

- [x] `meridian` Django app registered in `INSTALLED_APPS`.
- [x] Models on `HouseholdBaseModel` (household scoping, audit, soft-delete):
      `MeridianCategory`, `MeridianTask`, `MeridianPointsEntry`, `MeridianReward`,
      `MeridianRewardRequest`.
- [x] `MeridianTask` implements `CalendarSyncMixin`; dated tasks shadow a `CalendarEvent`.
- [x] Points accrue per **person** (ledger); approvals recorded against a **user** (D12).
- [x] `0001_initial` migration.

## Phase 2.1 — Logic: tasks, points, approvals, rewards (reuse the proven flow, D14)

- [x] Task lifecycle in services: `available → pending → approved | rejected`.
- [x] Points awarded **only on approval**; double-approve guarded; reject returns the task
      to `available` and awards nothing.
- [x] Rewards shop: request (balance checked), approve (deducts points, re-checks balance),
      reject (no deduction). Hot Tasks via `is_hot`. Manual points adjustment helper.
- [x] Calendar entries created/updated/deleted **only** via the scheduling helper (D7).

## Phase 2.2 — API (API Spec §14)

- [x] `GET/POST/GET/PATCH/DELETE /api/v1/meridian/tasks/[{id}/]`
- [x] `POST .../tasks/{id}/complete|approve|reject/`
- [x] `GET /api/v1/meridian/points/` (per-person summary + recent ledger)
- [x] `GET/POST /api/v1/meridian/rewards/`, `POST .../rewards/{id}/request/`
- [x] `GET /api/v1/meridian/reward-requests/`, `POST .../{id}/approve|reject/`
- [x] `GET/POST/PATCH/DELETE /api/v1/meridian/categories/[{id}/]`
- [x] `GET /api/v1/kiosk/meridian/` — kiosk-safe kid task/reward cards.
- [x] List selectors apply the visibility mixin; FTS search over tasks/rewards/categories (D9).

## Phase 2.3 — Permissions + security spine (D10)

- [x] `meridian.{view,create,edit,delete,approve,complete,request}` seeded with role grants.
- [x] **Narrow child-safe carve-out** in the resolver: children may only `complete` tasks
      and `request` rewards; the global child-write block stays intact for everything else.
- [x] Tests prove children can complete/request but cannot create/edit/delete/approve.

## Phase 2.4 — Node, Hub, kiosk integration

- [x] Meridian node enabled for the household (migration).
- [x] Hub widgets seeded + assembled: my tasks, hot tasks, points, pending approvals,
      reward requests. Kiosk-safe subset = my tasks, hot tasks, points.
- [x] Kiosk Meridian cards: large tap-to-complete task cards with a celebration, points
      display; no parent-facing widgets (approvals/requests) on the kiosk.

## Phase 2.5 — Data import (D14)

- [x] `import_meridian` management command — dry-runnable, idempotent for people/tasks/rewards,
      maps legacy users → people and tasks/points/rewards/history → the new tables.
- [x] `scripts/import_meridian.py` wrapper to run it from the repo root.

## Phase 2.6 — Frontend slice

- [x] API types + client methods for all Meridian endpoints.
- [x] `MeridianPage` (web): Tasks / Rewards / Points tabs; role-aware controls
      (create/approve/reject/delete for admin & manager; complete/request for everyone).
- [x] Kiosk Meridian widgets wired into the kiosk dashboard with completion + celebration.
- [x] Sidebar/bottom-nav entry. `tsc` + production build clean.

## Definition of done (Milestone 2)

- [x] Meridian runs entirely inside HomeStack — tasks, points, rewards, approvals, kid kiosk
      cards and celebrations — on shared users, permissions, Hub, Calendar and kiosk UI.
- [x] Household data can be imported one-time (dry-runnable) so the standalone app is retired.
- [x] Backend test suite green (279 tests; 30 new Meridian tests). Frontend builds clean.
