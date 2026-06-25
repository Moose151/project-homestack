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

## Phase 2.10 — Rewards shop parity
- [ ] Stock/quantity (`remaining_stock`, `disappear_when_empty`), `daily_limit_per_user`,
      `allow_multiple_in_cart`, `price_estimate`, `store_url`.
- [ ] Multiple reward images (carousel) via `attachments`.
- [ ] Cart + checkout flow; purchase lifecycle requested→approved/rejected/cancelled with
      reservation/refund.

## Phase 2.11 — Routines + streaks ✅ (2026-06-25)
- [x] `MeridianRoutine` + `MeridianRoutineCompletion` (one non-voided per person/routine/date);
      immediate points on completion (no approval); idempotent per day; API + child-safe complete.
- [x] Streak calculation (`current_streak`, `completed_today`); admin void claws back points.
- [~] `auto_end_streaks` household setting wired in 2.17 (streak helper already takes `auto_end`).

## Phase 2.12 — Group goals
- [ ] `GroupGoal` + `GroupGoalContribution`; progress %, funded; contribute (reserve) + refund;
      `group_goals_enabled` toggle.

## Phase 2.13 — Wishlist
- [ ] `WishlistRequest` → admin approve → `WishlistItem` (point cost) → `WishlistContribution`;
      funded/fulfilled; `wishlist_requests_enabled` toggle.

## Phase 2.14 — Achievements / badges (cross-node, D20)
- [ ] New shared `achievements` app: `Badge` (code/name/description/icon/criteria) +
      `PersonBadge` (household-scoped, per person).
- [ ] Awarding interface consumes the **events bus** (D4); nodes never call it directly.
- [ ] Seed the 15 Meridian badges; Meridian emits the relevant events; Hub surfaces a person's
      badges; kiosk celebrates a newly earned badge.

## Phase 2.15 — Notifications
- [ ] Wire the `notifications` app: task approved/rejected, reward approved/rejected, badge
      earned, allowance awarded. Surfaced on web + kiosk.

## Phase 2.16 — Scheduled command (D5 — cron, no in-process scheduler)
- [ ] One management command: weekly allowance awards (per-person amount + weekday), recurrence
      re-arm, streak auto-end, periodic badge re-checks (e.g. perfect-month). Idempotent.

## Phase 2.17 — Categories, settings, reports
- [ ] Separate task vs reward categories (admin-managed, active flag).
- [ ] Household settings via `NodeSetting`: `points_label`, `group_goals_enabled`,
      `wishlist_requests_enabled`, `auto_end_streaks`.
- [ ] Reports/leaderboard/recent-activity: points leaderboard, per-person summaries, earned/spent
      over time, task/reward activity feed.

## Phase 2.18 — Data import (D14) — full
- [ ] Extend `import_meridian` to a complete, **dry-runnable, idempotent** import: users →
      people/users; tasks/completions/rewards/purchases/point-ledger/routines/goals/wishlist/
      badges → new tables, preserving the ledger so **balances match the live app**.
- [ ] `scripts/import_meridian.py` runs it from the repo root with a `--dry-run`.

## Phase 2.19 — Frontend (web + kiosk) for the full set
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
