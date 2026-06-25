# Node Spec — Meridian (native)

> Canonical. **V1 node — migrated early.** Global rules from `00_README_and_Changelog.md`
> apply. Meridian is a **native HomeStack node**, not an external integration: its shell is
> rebuilt on shared services, its proven logic reused, and its live data imported (D13, D14).
> Existing standalone app: **`~/Documents/new/project-meridian`** (also
> github.com/Moose151/project-meridian) — the reference for logic *and* feature scope.
>
> **Scope correction (2026-06-25).** An earlier version of this spec under-scoped Meridian to
> "tasks · approvals · points · rewards · Hot Tasks · categories" and deferred everything else.
> That did not reflect the existing app, which the household uses daily. Per the owner, the
> native node must be a **full functional port** of the standalone app. This document now
> describes that full scope. See proposed decisions **D19/D20** at the bottom.

## 1. Purpose

Meridian is the household tasks, rewards and points system — incentivised chores and habits with
approval workflows, a points economy (shop, wishlist, group goals), achievements, and a
kid-facing kiosk experience. It already exists and is used daily; HomeStack brings it in
natively. Answers: *"What can household members do to earn points, and what can they spend or
work toward?"*

## 2. Philosophy

For incentivised tasks, habits and reward workflows — **not** general lists (Atlas) and not
school assessments (Education). Meridian is a primary kiosk node for children and one of the
highest-joy early wins, which is why it migrates right after the foundation and Atlas, ahead of
the sensitive nodes (it holds no sensitive data).

## 3. The points economy (the heart of the node)

A single **points ledger** is the source of truth for every balance — never a cached integer on
a person. In the legacy app this is `PointTransaction` (signed `amount` + `transaction_type`);
in HomeStack it is `MeridianPointsEntry` (signed `points`), **per person** (D12). All balances
are derived by summing the ledger.

- **Balance** = sum of all ledger entries for a person.
- **Total earned** = sum of *positive earning* entries only (types: `task_approved`,
  `routine_completed`, `allowance`, and manual positive adjustments). Spending, reservations,
  refunds and contributions do **not** reduce "total earned" — it is a lifetime stat used for
  badges and reports.
- Earning types: `task_approved`, `routine_completed`, `allowance`, `manual_adjustment`.
- Spending/holding types: `reward_requested` (negative reservation at request time),
  `reward_refunded` / `reward_cancelled_refund` (positive refund), `group_goal_contribution`,
  `wishlist_contribution`.
- **Reservation pattern (rewards & contributions):** points are deducted when a request/
  contribution is *made* (held), and refunded if it is rejected or cancelled. Approval does not
  deduct again. Refunds are idempotent (no double refund).

## 4. Feature set (full port)

Everything below exists in the standalone app and must be carried across. "Reuse the proven
logic" (D14) — port the rules, do not re-derive them.

**Tasks & approvals**
- Task definitions: `points`, optional `description`, category, assignment to a person,
  visibility, availability window, **completion scope** (per-person vs household/first-come).
- `completion_behavior`: `stay_active` (repeatable) vs `hide_after_approval` (one-off).
- **Recurrence** via weekday set (legacy `recurrence_days`) — expressed in HomeStack as a
  `recurrence_rule` (RRULE, D8); completions older than the cycle are ignored so the task
  re-appears. Dated tasks shadow a `CalendarEvent` via the scheduling helper (D7).
- **Hot Tasks**: `is_hot`, `hot_bonus_points`, `hot_label` — bonus added on approval.
- **Submission → review**: person submits a `TaskCompletion` (status `submitted`) with optional
  **photo evidence** (via the `attachments` app, D11); admin/manager approves (awards
  `point_value + hot_bonus`) or rejects (reason + optional review note; awards nothing). Admin
  may **complete-for-person** directly (bypass submit).
- Archive (hide without delete) distinct from soft-delete.

**Rewards shop**
- Reward: `cost_points`, description, category, `price_estimate`, `store_url`, **multiple
  images** (carousel), `quantity`/stock (`remaining_stock`, `disappear_when_empty`),
  `allow_multiple_in_cart`, `daily_limit_per_user`, active/archived.
- **Cart + checkout** (kiosk-friendly) and single-item request.
- Purchase lifecycle: `requested` (reserve points) → `approved` (fulfilled) | `rejected`
  (refund) | `cancelled` (refund).

**Routines & streaks**
- Daily habits; points awarded **immediately on completion, no approval** (`routine_completed`).
- One completion per person per routine per calendar date; completions can be **voided** by an
  admin (excluded from streaks/today-check).
- **Streaks**: consecutive completion dates; household setting `auto_end_streaks` controls
  whether a missed day breaks the streak automatically or only an admin can reset it.

**Group goals** — shared targets the household contributes points toward; progress %, funded
state, contribution ledger (refundable). Toggle: `group_goals_enabled`.

**Wishlist** — a person requests an item (`WishlistRequest`); admin approves it into a
`WishlistItem` with a point cost; the person contributes points over time
(`WishlistContribution`) until funded/fulfilled. Toggle: `wishlist_requests_enabled`.

**Achievements / badges** — see §6. Cross-node per the owner's call (D20).

**Allowance** — optional per-person weekly allowance (amount + weekday); awarded by the
scheduled command (D5), not an in-process scheduler.

**Categories** — admin-managed **task categories** and **reward categories** (separate kinds).

**Household settings** — `points_label` (e.g. "points"/"stars"/"tokens"), `group_goals_enabled`,
`wishlist_requests_enabled`, `auto_end_streaks`. Stored as `NodeSetting` rows (Phase 1.6), not a
new table.

**Reports & leaderboard** — points leaderboard, per-person summaries, recent-activity feed,
admin reports (earned/spent over time, task/reward activity).

**Notifications** — task approved/rejected, reward approved/rejected, badge earned, allowance
awarded — via the shared `notifications` app.

## 5. Native HomeStack changes (vs the standalone app)

- Uses shared **Users/People** and shared **avatar/PIN** auth — no separate Meridian users.
  Legacy `participation_enabled` (adults opt into earning) maps onto person/user config;
  `kiosk_pin_skip` (young children tap-to-login) maps onto the kiosk flow.
- Points accrue per **person**; every approval/adjustment records the acting **user** (D12).
- Calendar entries only via the scheduling helper (D7); recurrence as `recurrence_rule` (D8).
- Photo evidence and reward images via the `attachments` app (visibility + sensitivity, D11).
- Cross-node decoupling via the `events` signal bus (D4) — Meridian never imports another node's
  models, and the achievements system listens rather than being called directly.
- No APScheduler/Celery (D5) — allowance, recurrence reset, streak auto-end and periodic badge
  checks run in a Django management command on cron.

## 6. Achievements / badges — cross-node (D20)

Per the owner: badges live at a **shared, cross-node level** (surfaced on the Hub) so children
earn recognition across *all* nodes, not just Meridian.

- New shared app (proposed `apps/achievements`): `Badge` (code/name/description/icon/criteria),
  `PersonBadge` (awarded, per person, with `earned_at` and source). Household-scoped.
- A thin awarding interface; nodes **publish events** (D4) and the achievements app **consumes**
  them and evaluates criteria — no node calls another node's models.
- Meridian seeds and emits its badge-relevant events (task counts, routine streaks/totals,
  perfect month, wishlist saver/funded, group contributor, earning milestones — the 15 legacy
  badges). Other nodes (Education, Pets, …) can register their own badges later with no Meridian
  changes.
- Hub shows a person's badges; kiosk shows a celebration when a badge is earned.

## 7. Permissions (D10)

Resolver actions: `meridian.{view, create, edit, delete, approve, complete, request,
contribute, adjust}`.
- Admins/managers: manage tasks/rewards/routines/goals/wishlist, approve, adjust points.
- Users/children: view their tasks/points/rewards; **complete** tasks, **request** rewards,
  **contribute** to goals/wishlist. The global child-write block stays intact except this narrow
  carve-out (already established for complete/request — extend to contribute).
- Admin/financial settings and reports hidden from non-managers. No sensitive-node re-auth
  required (no sensitive data), unlike Solace.

## 8. Hub integration

Widgets: my tasks · hot tasks · pending approvals · points summary · reward requests · my badges
· routines-due-today · group-goal progress. Kiosk-safe subset: my tasks · hot tasks · routines ·
points · my badges (no approvals/requests/reports on kiosk).

## 9. Calendar integration

Events for dated/recurring tasks, due tasks, reward/goal deadlines — via the scheduling helper;
recurrence as `recurrence_rule` (D7, D8).

## 10. Events (signals, D4)

Publishes: `task_created`, `task_completed`, `task_approved`, `task_rejected`,
`routine_completed`, `reward_requested`, `reward_approved`, `points_awarded`,
`goal_contributed`, `wishlist_funded`. Consumes (future): `homework_created`,
`pet_care_task_created`, `inventory_task_created`, `project_task_created`. The achievements app
consumes the points/task/routine/goal/wishlist events.

## 11. Search

FTS (D9) over task names, reward names, routine titles, goal/wishlist names, categories — and
task/reward history — permission-aware.

## 12. Kiosk

A primary kiosk experience: large task & routine cards (tap-to-complete with celebration),
reward shop + cart, points display, wishlist/goal progress, badge celebrations, avatar-based
context, minimal typing. `kiosk_pin_skip` people log in by tapping their card.

## 13. Scheduled work (D5)

A single management command (cron) handles: weekly allowance awards, recurrence reset (re-arm
recurring tasks), streak auto-end (when enabled), and periodic badge re-checks (e.g.
perfect-month). No in-process scheduler.

## 14. Migration plan (D14)

1. **Rebuild the shell** — extend the `meridian` app with native models on `HouseholdBaseModel`
   for the full feature set (routines, goals, wishlist, richer tasks/rewards), plus the shared
   `achievements` app. Serializers, thin views, urls, permissions via the resolver, kiosk
   endpoints.
2. **Reuse the logic** — port the points ledger rules, reservation/refund flow, completion
   behaviours, recurrence, streak calculation, badge criteria and allowance from the standalone
   app rather than re-deriving them.
3. **Import the data** — a one-time, **dry-runnable, idempotent** script in `scripts/` mapping
   legacy users → HomeStack people/users and tasks/completions/rewards/purchases/point-ledger/
   routines/goals/wishlist/badges → the new tables, preserving the ledger so balances match.
4. **Cut over** — once verified against the live data, the family stops using the standalone app.

## 15. V1 scope (as a native node) — full port

Tasks (recurrence, hot, evidence, behaviours, assignment/scope) · approvals · points ledger ·
rewards shop (stock, daily limits, images, cart) · routines + streaks · group goals · wishlist ·
cross-node badges · allowance · categories (task + reward) · household settings · reports +
leaderboard + activity feed · notifications · Hub widgets · kiosk cards · calendar integration ·
imported household data.

## 16. Completion criteria

Meridian runs entirely inside HomeStack — tasks, routines, points, rewards/shop, group goals,
wishlist, approvals, badges, allowance, reports, kid kiosk cards and celebrations — using shared
users, permissions, Hub, Calendar, notifications and kiosk UI, with the household's existing data
imported and balances matching, and the standalone app retired at home.

## 17. Proposed new decisions (ratify on sign-off)

- **D19 — Meridian is a full functional port of the standalone app.** The native node carries
  the complete feature set above; the earlier reduced scope is superseded.
- **D20 — Achievements/badges are a shared cross-node system**, not Meridian-local. A
  household-scoped `achievements` app awards badges via the events bus (D4); the Hub surfaces
  them; any node can register badges. Meridian is the first producer.
