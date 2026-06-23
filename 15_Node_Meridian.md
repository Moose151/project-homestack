# Node Spec — Meridian (native)

> Canonical. **V1 node — migrated early.** Global rules from `00_README_and_Changelog.md`
> apply. Meridian is a **native HomeStack node**, not an external integration: its shell is
> rebuilt on shared services, its proven logic reused, and its live data imported (D13, D14).
> Existing standalone app: github.com/Moose151/project-meridian (reference for logic/data).

## 1. Purpose

Meridian is the household tasks, rewards and points system — incentivised chores with approval
workflows and a kid-facing kiosk experience. It already exists and is used daily in the
household; HomeStack brings it in natively. Answers: *"What tasks can household members
complete for rewards or recognition?"*

## 2. Philosophy

For incentivised tasks and reward workflows — **not** general lists (Atlas) and not school
assessments (Education, though Education may generate rewarded tasks). Meridian is a primary
kiosk node for children and one of the highest-joy early wins, which is why it migrates right
after the foundation and Atlas, ahead of the sensitive nodes (it holds no sensitive data).

## 3. What belongs

Clean-bedroom-for-points; feed-the-pets-for-points; read-15-minutes as a rewarded task; help
unpack groceries; do dishes; reward-shop requests; task approvals; points adjustments;
achievement badges.

## 4. What does NOT belong

General shopping lists → Atlas. School assignments → Education (may create Meridian tasks).
Bills/budgets → Solace. Pet treatment records → Pets. General project tasks → Projects (unless
they're rewarded household tasks).

## 5. Primary users

Admins manage tasks, rewards and approvals. Managers may manage tasks/approvals if permitted.
Users/children complete tasks and request rewards. Primary kiosk node for children.

## 6. Key features

**Carried over from the existing app (reuse the proven logic):** tasks, task approvals, points
ledger, rewards shop, Hot Tasks, categories, admin management, household settings, user cards.

**Native HomeStack additions / changes:**
- Uses shared **Users/People** (no separate Meridian users) and shared **avatar/PIN** auth.
- Tasks may carry `assigned_to_person`, `due_at`, `recurrence_rule`, `calendar_event_id`.
- Points accrue per **person**; approvals recorded against a **user**.
- Hub widgets and kiosk cards use the shared design system.
- Future: achievements, streaks, weekly summaries, task templates, plus Education/Pets/
  Inventory-generated tasks via signals.

## 7. Permissions

Children view their tasks, points and rewards. Admins/managers approve tasks and manage
rewards. Admin/financial settings hidden from users. No sensitive-node re-auth required (no
sensitive data), unlike Solace.

## 8. Hub integration

Widgets: my tasks · hot tasks · pending approvals · points summary · reward requests ·
achievements.

## 9. Calendar integration

Events for recurring tasks, due tasks, reward events and deadlines — via the scheduling helper;
recurrence as `recurrence_rule`.

## 10. Notifications

Task approved/rejected · reward approved · task due · approval pending.

## 11. Events (signals)

Publishes: `task_created`, `task_completed`, `task_approved`, `task_rejected`,
`reward_requested`, `reward_approved`, `points_awarded`.
Consumes: `homework_created`, `pet_care_task_created`, `inventory_task_created`,
`project_task_created`.
Example: Education `homework_created` → Meridian creates a rewarded reading task → child
completes on kiosk → parent approves.

## 12. Search

FTS over task names, reward names, task history, categories — permission-aware.

## 13. Kiosk

A primary kiosk experience: large task cards, reward cards, points display, celebrations,
simple completion, avatar-based context, minimal typing.

## 14. Migration plan (D14)

1. **Rebuild the shell** — `meridian` Django app with native models on `HouseholdBaseModel`,
   serializers, views, urls, permissions (via the resolver), kiosk endpoints.
2. **Reuse the logic** — port the reward/points/approval calculation and Hot Tasks behaviour
   from the existing app rather than re-deriving it.
3. **Import the data** — a one-time, dry-runnable script in `scripts/` mapping existing
   Meridian users → HomeStack people/users, and tasks/points/rewards/history → the new tables.
4. **Cut over** — once verified, the family stops using the standalone app.

## 15. V1 scope (as a native node)

Tasks · approvals · points · rewards shop · Hot Tasks · categories · Hub widgets · kiosk cards
· calendar integration · imported household data.

## 16. Completion criteria

Meridian runs entirely inside HomeStack — tasks, points, rewards, approvals, kid kiosk cards
and celebrations — using shared users, permissions, Hub, Calendar, notifications and kiosk UI,
with the household's existing data imported and the standalone app retired at home.
