# Node Spec — Solace (native)

> Canonical. **Later node — migrated after security maturation** (Roadmap M5). Sensitive
> throughout. Global rules from `00_README_and_Changelog.md` apply. Solace is a **native
> HomeStack finance node**, not an external integration: shell rebuilt on shared services,
> proven logic reused, live data imported (D13, D14).
> Existing standalone app: github.com/Moose151/project-solace (reference for logic/data).

## 1. Purpose & philosophy

Solace is the household bills, budgeting and planned-purchase system. It already exists and is
used in the household; HomeStack brings it in natively — but only after the security foundation
is mature, because it holds financial data. Answers: *"What money needs to be set aside, what
bills are due, and what planned purchases are coming?"* **Sensitive; protected by
re-authentication.**

## 2. Belongs / does not belong

**Belongs:** electricity/rent/mortgage/insurance bills, streaming subscriptions, planned
purchases, set-asides, budget buckets, payday checklist, travel budget, (future) grocery budget.
**Not:** shopping lists → Atlas; meal plans → Hearth; asset records → Assets; receipts → linked
via Documents/Attachments; children's tasks → Meridian.

## 3. Primary users

Admins access Solace. Managers access if granted. Standard users and children do **not** see
Solace by default.

## 4. Key features

**Carried over (reuse the proven logic):** recurring bills, planned purchases, savings buckets,
payday checklist, calendar/list views, categories, authentication, backups.
**Native HomeStack additions / changes:**
- Uses shared Users/People, attachments and permissions.
- `sensitivity = financial`; sensitive-node locking and re-auth via the central resolver.
- Financial calendar events via the scheduling helper; `recurrence_rule` for recurring bills.
- Permission-controlled Hub finance widgets; subscription tracking; attachment support.

## 5. Permissions (strong)

Default admin-only, optional manager access, hidden from users/children. **Re-authentication
required** before opening. **All access audited.** Finance must never appear in unauthorised
Hub, Calendar, Search or kiosk views.

## 6. Hub / Calendar / Notifications

Widgets (permission-controlled, never for children/unauthorised): bills due · payday upcoming ·
planned-purchase reminder · subscription renewal · set-aside summary. Calendar (via helper):
bills due, paydays, subscription renewals, planned-purchase dates, savings milestones — hidden
from unauthorised users. Notifications to authorised users: bill due/overdue · payday ·
subscription renewal · planned purchase approaching.

## 7. Events (signals)

Publishes: `bill_due`, `bill_paid`, `payday_due`, `planned_purchase_due`, `subscription_due`,
`budget_threshold_reached`.
Consumes: `travel_trip_created`, `hearth_grocery_estimate_created`, `asset_purchase_created`.
Example: Travel creates a trip → Solace creates an optional travel budget/set-aside.

## 8. Search / Kiosk

Restricted FTS — financial results only for authorised users with sensitive access. No child
kiosk interface; kiosk access disabled by default. If an admin opens Solace on kiosk, re-auth
and a short timeout are required.

## 9. Migration plan (D14)

1. **Rebuild the shell** — `solace` Django app with native models on `HouseholdBaseModel`,
   `sensitivity = financial`, re-auth-gated endpoints via the resolver.
2. **Reuse the logic** — port bill-recurrence, set-aside/bucket and payday-checklist behaviour.
3. **Import the data** — a one-time, dry-runnable script in `scripts/` mapping existing Solace
   data onto the new tables and onto shared users/people.
4. **Cut over** — only after security maturation (M4) is proven; then retire the standalone app
   at home.

## 10. Data model

`solace_bills` (`recurrence_rule`, `calendar_event_id`), `solace_paydays`,
`solace_planned_purchases`, `solace_buckets`, `solace_subscriptions`,
`solace_payday_checklist_items`. Inherit `HouseholdBaseModel`; all `sensitivity = financial`.

## 11. Scope & completion

Initial (native): bills · paydays · planned purchases · buckets/set-asides · subscriptions ·
payday checklist · permission-controlled Hub/Calendar · re-auth · audit · imported data.
Complete when only authorised users access Solace through HomeStack, re-auth works, finance
never leaks into unauthorised views, and the standalone app is retired at home. Future:
richer subscriptions, travel/grocery/asset-purchase budget integration, financial documents,
export/reporting, encrypted finance fields.
