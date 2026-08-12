# Node Spec — Meridian (native)

> **Status:** shipped native HomeStack domain and household source of truth for tasks/rewards/points
> (D13/D14/D19). Achievements are a shared cross-domain capability (D20). The standalone Meridian
> repository remains a historical/behaviour reference, not an active integration layer or required
> runtime dependency.

## 1. Purpose

Meridian is the household incentive system: rewarded tasks and routines, approvals, points,
rewards/shop, group goals, wishes and achievements with a child-friendly experience and an efficient
adult management cockpit.

It answers: **What can household members do to earn points, what is waiting for review, and what can
they spend/save/contribute toward?**

Meridian does not own ordinary household to-dos (Atlas) or school assessments (Education).

## 2. Source-of-truth position

HomeStack is the Meridian source of truth.

- Meridian uses shared HomeStack Users/People/authentication/permissions.
- The standalone app is not embedded/iframed and is not a second writable data source.
- Legacy logic/data informed the native port and importer, but normal operation does not depend on
  the standalone repository being present.
- Adult setup/review/reporting lives in HomeStack; child-facing presentation may continue to evolve
  around the same HomeStack APIs/data without creating another backend.

If referring to a local standalone checkout for behavioural comparison, resolve the actual current
path rather than assuming the obsolete `~/Documents/new/project-meridian` location recorded in old
handover history.

## 3. Points ledger — core invariant

A signed per-Person points ledger is the source of truth for balances. Do not cache a mutable balance
integer as the authoritative value.

Key semantics:

- **Balance** = sum of the Person's signed ledger entries.
- **Lifetime/total earned** counts positive earning entries, not current balance.
- Spending/reservations/contributions reduce available balance but do not erase lifetime earned.
- Reward requests/contributions use the established reservation pattern: deduct/hold at request or
  contribution time; refund exactly once if rejected/cancelled; approval does not deduct twice.
- Manual adjustments are auditable and attributed to the acting User.

Any feature that awards/refunds points must use the shared ledger/service rules rather than update a
Person aggregate independently.

## 4. Tasks and completion review

Tasks support the implemented combination of:

- title/description/category;
- base points and Hot Task bonus/label;
- Person assignment and applicable scope/availability;
- repeatable vs hide-after-approval behaviour;
- weekday/recurrence behaviour expressed through the established recurrence contract;
- due-date Calendar integration where applicable;
- archive vs delete;
- per-Person/household completion semantics.

The native completion model records a submission/review lifecycle rather than treating "clicked"
as automatically approved reward work.

Typical flow:

```text
available task
 -> Person submits completion
 -> submitted/pending completion
 -> manager/admin approves or rejects
 -> approval awards points exactly once
```

Review can retain rejection/review notes/history. Admin complete-for-Person behaviour can bypass the
ordinary submission step where intentionally supported.

Photo/evidence remains optional enhancement territory unless the current implementation explicitly
supports it; files use shared Attachments rather than Meridian-owned storage.

## 5. Rewards shop

The rewards system supports the implemented richer household shop model including relevant fields
such as:

- point cost;
- description/category;
- stock/remaining quantity and hide-when-empty behaviour;
- daily/per-user limits;
- multi-item/cart behaviour where implemented;
- store/reference/image information;
- active/archive state.

Purchase/request lifecycle preserves the points reservation/refund invariant.

The adult cockpit manages catalogue, stock, pending requests and fulfilment. The child-facing
surface emphasizes choosing rewards and understanding available points without exposing admin
complexity.

## 6. Routines and streaks

Routines represent repeatable habits that can award points according to the established native
rules.

Important invariants:

- one Person's completion does not incorrectly satisfy another Person's routine;
- repeat/date rules use household-local date semantics;
- void/reset/admin behavior preserves history rather than rewriting the ledger invisibly;
- streak calculation follows the configured household behavior rather than an ad-hoc frontend
  counter.

## 7. Goals and wishes

### Group goals

Household members can contribute points toward a shared target. Contributions use ledger entries so
the funded state is derived/explainable and rejected/cancelled/refunded flows remain auditable.

### Meridian wishlist

Meridian owns **points-based** wishes/reward-saving workflows. This is distinct from Atlas personal
lists/ordinary point-free wishes shown in Corners.

The same Meridian wishlist records can appear in a Person's Corner as a permission-filtered
projection. They are not copied into Atlas.

Product URLs can use the shared Link Import capability where useful, while approval/point ownership
remains Meridian.

## 8. Achievements / badges (D20)

Achievements are a shared cross-domain capability, not a Meridian-only database.

Meridian publishes meaningful task/routine/points/goal/wish events. The shared achievements
capability evaluates applicable criteria and records Person badges. Other domains such as Education
or Fitness can also contribute without importing Meridian models.

Hub/Corners/kiosk can display permitted badge information and celebrations.

D20 is ratified/current; it is not a proposal waiting for sign-off.

## 9. Allowance and scheduled work

Optional allowance/periodic Meridian processing uses the scheduled management-command pattern (D5),
not an in-process scheduler.

Scheduled operations must be:

- household-timezone aware;
- idempotent/catch-up safe;
- safe to rerun after interruption;
- auditable where points are changed.

Do not add Celery merely because allowance is scheduled.

## 10. Categories/settings/reports

Meridian supports the current management set for task/reward categories, household Meridian
settings, leaderboard/Person summaries, points/activity reports and other adult-cockpit views.

Settings use the shared node/settings capability where appropriate rather than inventing another
configuration subsystem.

## 11. Permissions

Meridian uses central permissions for the relevant actions such as view/create/edit/delete,
approve, complete, request, contribute and points adjustment.

Broad intent:

- managers/admins manage catalogue/workflows/reviews and permitted points adjustments;
- ordinary Users/children can perform the explicitly allowed Person-facing actions;
- the child-write carve-outs are narrow domain permissions, not permission to bypass D10;
- adult reporting/settings are hidden from children/non-managers as appropriate.

Meridian is not a sensitive-node-by-default domain like Solace/Health, but private/restricted records
still follow normal visibility rules.

## 12. Hub / Calendar / Notifications

Meridian can contribute permission-aware summaries including today's tasks/routines, Hot Tasks,
points, badges, goals and review queues.

Dated/recurring task information follows D7/D8 Calendar ownership rules.

Notifications use the shared Notifications/Web Push infrastructure for meaningful events such as
approval/rejection, reward state, badges and allowance. Meridian does not implement its own push
channel.

## 13. Search and kiosk

Search covers permitted tasks/rewards/routines/goals/wishes/categories/history according to current
selectors.

Meridian is one of the strongest kiosk/child domains: large task/routine cards, points/reward state,
shop/goals/wishes/badges and minimal typing. The adult management cockpit is a separate responsive
web experience rather than being squeezed into the child kiosk UI.

## 14. Events (D4)

Meridian publishes stable meaningful events around task completion/review, routines, reward state,
points, goals/wishes and achievements inputs.

Other domains consume those through D4 rather than importing Meridian models. Likewise future
Education/Pets/Home Assistant relationships use events/shared services and preserve ownership.

## 15. Legacy import tooling (D14)

The legacy importer remains useful migration/recovery tooling. It should preserve ledger history and
map legacy subjects to HomeStack People/Users safely, with dry-run/idempotent behavior where
practical.

The household native migration/cutover is complete. Therefore "import Meridian and retire the
standalone app" is historical work, not an open roadmap item.

## 16. Completion state

D19 is satisfied: Meridian is a full functional native HomeStack domain rather than the originally
under-scoped tasks/points demo.

The current baseline includes the real points ledger/reservation semantics, tasks/completion review,
routines, rewards/shop, goals/wishes, achievements, allowance/settings/reporting, Hub/notifications,
adult management and child-friendly workflows.

Future Meridian work should be driven by observed household friction/delight opportunities rather
than another migration/parity project.