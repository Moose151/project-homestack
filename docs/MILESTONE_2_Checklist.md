# Milestone 2 — Native Meridian: Build Checklist

> Canonical for M2. Global rules from `00_README_and_Changelog.md` (D1–D18, + proposed
> D19/D20) apply. Source node spec: `15_Node_Meridian.md` (full-port scope). Reference app:
> `~/Documents/new/project-meridian`. Built on the proven Atlas pattern (models → services →
> selectors → serializers → thin views → urls → permissions → calendar/events helpers → tests).
>
> Checkbox legend: `[ ]` todo · `[~]` partial/needs work · `[x]` done.
>
> **2026-06-25 status reset.** M2 was previously marked 100% complete. That was inaccurate: only
> a thin tasks/points/rewards foundation was built, and it was unusable from the browser (a
> CSRF write bug, fixed 2026-06-25). The legacy app's routines, group goals, wishlist, badges,
> allowance, shop depth (stock/limits/images/cart), reports/leaderboard, notifications and
> separate task/reward categories were never ported. This checklist now reflects true scope.

---

## Part A — Foundation already built (verify, don't rebuild)

## Phase 2.0 — App + base models
- [x] `meridian` app registered; `MeridianCategory`, `MeridianTask`, `MeridianPointsEntry`,
      `MeridianReward`, `MeridianRewardRequest` on `HouseholdBaseModel`.
- [x] `MeridianTask` uses `CalendarSyncMixin`; `0001_initial` migration; node enabled (`0002`).

## Phase 2.1 — Core flow (tasks → approval → points → rewards)
- [x] Task lifecycle `available → pending → approved | rejected`; points on approval only;
      double-approve guarded.
- [x] Rewards request → approve (deduct) → reject; `is_hot` flag; manual points adjustment.
- [x] Calendar entries via the scheduling helper (D7).

## Phase 2.2 — Core API + permissions
- [x] Tasks/categories/points/rewards/reward-requests endpoints; child carve-out for
      complete/request; `meridian.*` permissions seeded.
- [x] Kiosk endpoint + initial Hub widgets + frontend `MeridianPage` (tabs) + import-command
      stub for the subset.

> **Reality check on Part A:** the ledger here is a simplified `MeridianPointsEntry`, not the
> legacy signed-transaction model with reservation/refund + "total earned vs balance". Rewards
> have no stock/limits/images/cart. Tasks have no recurrence/behaviour/evidence/scope. These are
> addressed in Part C.

---

## Part B — Make the foundation actually work (do first)

## Phase 2.7 — Write path + wire up existing UI
- [x] **Fix CSRF write bug** — `ensure_csrf_cookie` on `GET /auth/me/`; client sends
      `X-CSRFToken` on unsafe methods. (Done 2026-06-25; verify live: add task/reward/list.)
- [ ] Surface API errors in the UI (the create handlers currently swallow failures).
- [ ] Hot-task toggle + bonus points in the task form; category pickers wired.
- [ ] Category management UI (create/rename/activate task & reward categories).
- [ ] Verify Hub + kiosk Meridian widgets render real data end-to-end.

---

## Part C — Port the missing feature set (the bulk of M2)

> Each phase: models (+migration) → services (port the rules) → selectors (visibility + FTS) →
> serializers → thin views → urls → permissions → events (D4) → web UI → kiosk UI → tests.

## Phase 2.8 — Points ledger parity ✅ (2026-06-25)
- [x] Reworked the ledger to typed signed transactions (`MeridianPointsEntry.TransactionType`:
      task_approved, routine_completed, allowance, manual_adjustment, reward_requested,
      reward_refunded, reward_cancelled_refund, + goal/wishlist types reserved for 2.12/2.13).
- [x] `get_points_balance` = sum(ledger); `get_total_earned` = positive earning types only.
- [x] **Reservation/refund pattern**: rewards reserve on request, refund on reject/cancel,
      idempotent (`_refund_reservation`); approval no longer double-deducts.

## Phase 2.9 — Tasks parity 🟡 (2026-06-25 — additive done; completion-history deferred)
- [x] `completion_behavior` (stay_active / hide_after_approval; one-off hides on approval);
      `is_archived` (archive) vs soft-delete; `is_active` published flag.
- [x] Assignment to person, visibility, `availability_window`, `completion_scope` (fields).
- [x] Hot tasks: `hot_bonus_points` + `hot_label`; `award_value` includes the bonus on approval.
- [~] Recurrence: `recurrence_rule` + `due_at` sync to calendar (D7) already work; **cycle-based
      re-arming deferred** to the completion model + scheduled command (2.16).
- [ ] **Deferred to a `MeridianTaskCompletion` model**: per-person completion history, shared
      (first-come) completion by multiple people, recurring re-arm, photo **evidence** via
      `attachments` (D11), review notes, admin complete-for-person. *(Current model folds a single
      status onto the task — fine for assigned chores; the completion table is needed for shared/
      recurring tasks. Tracked as Phase 2.9b.)*

## Phase 2.10 — Rewards shop parity 🟡 (2026-06-25 — carousel deferred)
- [x] Stock/quantity (`remaining_stock`, `disappear_when_empty`), `daily_limit_per_user`,
      `allow_multiple_in_cart`, `price_estimate`, `store_url`, `image_url`, `is_archived`.
- [x] Cart + checkout (`checkout_cart`, all-or-nothing); purchase lifecycle reservation/refund
      (request→approve/reject/cancel) from 2.8.
- [ ] Multiple uploaded reward images (carousel) via `attachments` — deferred to the attachments
      pass (single `image_url` works for now).

## Phase 2.12 — Group goals ✅ (2026-06-25)
- [x] `MeridianGroupGoal` + `MeridianGroupGoalContribution`; progress %, funded; contribute
      (reserve) + refund; child-safe `contribute` (resolver carve-out + `meridian.contribute`
      permission seeded). Full API.

## Phase 2.13 — Wishlist ✅ (2026-06-25)
- [x] `MeridianWishlistRequest` → admin approve → `MeridianWishlistItem` (point cost) →
      `MeridianWishlistContribution`; funded/fulfilled; child-safe request + contribute. Full API.

## Phase 2.11 — Routines + streaks ✅ (2026-06-25)
- [x] `MeridianRoutine` + `MeridianRoutineCompletion` (one non-voided per person/routine/date);
      immediate points on completion (no approval); idempotent per day; API + child-safe complete.
- [x] Streak calculation (`current_streak`, `completed_today`); admin void claws back points.
- [~] `auto_end_streaks` household setting wired in 2.17 (streak helper already takes `auto_end`).

> Group goals (2.12) and wishlist (2.13) are listed above, before 2.11 (built same day).
> Their `group_goals_enabled` / `wishlist_requests_enabled` toggles land with settings in 2.17.

## Phase 2.14 — Achievements / badges (cross-node, D20) 🟡 (2026-06-25 — perfect_month + UI deferred)
- [x] New shared `apps/achievements`: `Badge` (global catalogue), `PersonBadge`
      (household-scoped), `AchievementCounter` (app-owned per-person tallies → stays decoupled).
- [x] Awarding via the **events bus** only (`handlers.connect()` in AppConfig.ready); the app
      never imports Meridian models (D4). Meridian events enriched (routine `streak`, points
      `transaction_type`, new `wishlist_contributed`).
- [x] 15 Meridian badges seeded; awarded on task/routine/goal/wishlist/points events; idempotent.
      `GET /achievements/badges/` + `/achievements/my-badges/`; `achievements.view` for all roles.
- [ ] `routine_perfect_month` evaluated in the scheduled command (2.16); Hub badge widget +
      kiosk celebration land with the frontend (2.19).

## Phase 2.15 — Notifications 🟡 (2026-06-25 — UI in 2.19)
- [x] Built the `notifications` app (shared infra: `Notification`, services, selectors,
      `GET /notifications/` + read/read-all, `notifications.view` perm migration 0011).
- [x] Wired: task approved/rejected, reward approved/rejected, badge earned. Allowance awarded
      lands with the scheduled command (2.16).
- [ ] Web/kiosk notification UI (bell + list) lands with the frontend (2.19).

## Phase 2.16 — Scheduled command (D5 — cron, no in-process scheduler) 🟡 (2026-06-25)
- [x] `meridian_run_scheduled` management command (cron-friendly, `--date`/`--skip-*` flags).
- [x] Weekly allowance: `MeridianAllowance` (per-person amount + weekday), `award_allowances`,
      idempotent per day (keyed on the date in the reason). Notifies the person.
- [x] Perfect-month routine badge via the achievements bus (`award_perfect_month_badges` →
      `meridian.routine_perfect_month` → achievements awards). Idempotent.
- [x] Streak auto-end needs no job (computed at read time from completions + the setting).
- [ ] Recurring-task re-arm is part of the deferred task-completion model (2.9b).
- [ ] Allowance config UI/endpoint lands with settings (2.17) / frontend (2.19).

## Phase 2.17 — Categories, settings, reports ✅ (2026-06-25)
- [x] Task vs reward categories via `MeridianCategory.kind` (filterable `?kind=`).
- [x] Household settings via `NodeSetting` (`apps/meridian/config.py`): `points_label`,
      `group_goals_enabled`, `wishlist_requests_enabled`, `auto_end_streaks`; `GET/PATCH
      /meridian/settings/` (PATCH = manager). Toggles enforced in goal/wishlist services;
      `auto_end_streaks` drives `current_streak`.
- [x] `GET /meridian/reports/`: leaderboard (balance, lifetime earned, badge count) + recent
      activity feed.

## Phase 2.18 — Data import (D14) — full ✅ (2026-06-25)
- [x] Extended `import_meridian` (dry-runnable) to the full set: users→people, categories (kind),
      tasks, rewards, point-ledger (with `transaction_type` so **balance AND lifetime-earned
      match**), reward requests, routines + completions, group goals + contributions, wishlist
      items/contributions/requests, earned badges, allowances. Entities idempotent via natural
      keys; ledger/contribution history is append-only (run once or after a wipe).
- [x] `scripts/import_meridian.py` wrapper runs it from the repo root (supports `--dry-run`).

## Phase 2.19 — Frontend (web + kiosk) for the full set
> **Approach (owner, 2026-06-25):** rebuild each screen to **match the legacy Meridian HTML
> templates** (`~/Documents/new/project-meridian/app/templates/`), adapted to HomeStack's warm
> design system. Build **each feature on web + kiosk together**, feature by feature.
> Part 1 (API types + client for every endpoint) — done. Screens in progress below.
>
> Per-feature progress (web + kiosk):
> - [x] **Tasks** — web board matches legacy (filters, hot/behaviour/category/assignee badges,
>   base+bonus points, role-aware actions, full create form); kiosk tap-to-complete cards +
>   celebration (uses `award_value`).
> - [x] **Shop / rewards** — web: balance banner, product cards (image/cost/stock/price/store),
>   client-side cart + checkout, admin create (stock/limits/image) + pending approvals; kiosk:
>   tap-to-request reward cards + celebration. *(reward→category link not in backend; no category
>   filter on shop)*
> - [ ] Routines + streaks + kiosk routine cards
> - [ ] Group goals + Wishlist (+ progress) + kiosk
> - [ ] Points / Leaderboard / Badges + kiosk badge celebration
> - [ ] Approvals + Settings (web) + notification bell
- [ ] Web: Tasks · Shop/Rewards · Routines · Goals · Wishlist · Points/Leaderboard · Badges ·
      Approvals · Categories/Settings (role-aware).
- [ ] Kiosk: task & routine cards (tap-to-complete + celebration), shop + cart, goal/wishlist
      progress, badge celebration. `kiosk_pin_skip` tap-to-login.
- [ ] API types/client for all endpoints; `tsc` + production build clean.

---

## Definition of done (Milestone 2)

- [ ] Meridian runs entirely inside HomeStack as a **full port**: tasks (recurrence, hot,
      evidence, behaviours), approvals, points ledger, rewards/shop (stock, limits, images,
      cart), routines + streaks, group goals, wishlist, cross-node badges, allowance, reports +
      leaderboard, notifications — on shared users/permissions/Hub/Calendar/kiosk.
- [ ] Household data imported one-time (dry-runnable) with **balances matching** the live app;
      standalone app retired at home.
- [ ] Backend test suite green (existing + new); frontend builds clean.
