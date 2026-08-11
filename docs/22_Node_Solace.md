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
- Permission-controlled Hub finance widgets; subscriptions as recurring Bills; attachment support.
- Native pay-cycle planning: recurring paydays feed percentage/fixed bucket allocation rules,
  fixed household amounts split proportionally by income, with one-click cycle checklist creation.
- Recurring bills materialise independent due-date occurrences. Each occurrence can be paid,
  restored or skipped without changing the recurrence definition; the Solace Schedule combines
  monthly bill occurrences and expected income in calendar/list views.
- Full standalone-parity management: custom categories and normalised reports, current/next pay
  plans and checklists, account-balance projections, finance health checks, current/next cycle
  closeout, required set-aside/shortfall reporting, hidden checklist preferences and complete
  edit/delete workflows.
- Bills-account cash-flow forecast over 3–24 months: expected Bills-bucket transfers less
  included bill occurrences (including Subscription-category bills), with a dated running balance, lowest
  point, first risk date, required opening balance and safe-to-withdraw values both before and
  after the configured buffer. A balance recorded today is treated as an end-of-day value;
  otherwise the latest snapshot is the current known opening balance and Finance Health warns
  once it is more than 14 days old. Only active buckets whose category contains “Bills” count
  as account transfers.
- Readable CSV/XLSX exports, reviewed ad-hoc CSV/XLSX bill import and an expanded idempotent
  standalone SQLite importer.
- Single-entry Homestead handoff: an explicitly classified bill can create or claim its richer
  home-insurance, household-service or paid-maintenance record through events. Existing bills can
  be organised later without retyping. Homestead then owns descriptive edits while Solace keeps
  the financial occurrence/payment history.
- Reverse maintenance handoff: an existing Homestead task can request its one Solace cost with an
  amount; repeat requests update the same source-linked bill and retain Solace payment ownership.

## 5. Permissions (strong)

Default admin-only, optional manager access, hidden from users/children. **Re-authentication
required** before opening. **All access audited.** Finance must never appear in unauthorised
Hub, Calendar, Search or kiosk views.

## 6. Hub / Calendar / Notifications

Widgets (permission-controlled, never for children/unauthorised): bills due · payday upcoming ·
planned-purchase reminder · subscription renewal · set-aside summary. Calendar (via helper):
bills due (including subscriptions), paydays, planned-purchase dates, savings milestones — hidden
from unauthorised users. Notifications to authorised users: bill due/overdue · payday ·
subscription renewal · planned purchase approaching. Run the idempotent reminder command daily:
`docker exec homestack-backend python manage.py solace_run_scheduled`.

## 7. Events (signals)

Publishes: `bill_due`, `bill_paid`, `payday_due`, `planned_purchase_due`,
`budget_threshold_reached`, `homestead_record_requested`.
Consumes: `homestead.insurance_policy_saved`, `homestead.household_cost_saved`,
`homestead.maintenance_cost_requested`, `homestead.maintenance_saved/deleted`,
`travel_trip_created`, `hearth_grocery_estimate_created`, `asset_purchase_created`.
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
   data onto the new tables and onto shared users/people. Run `import_solace --dry-run`, apply
   the import, then run `import_solace --verify`; verification is read-only and reports any
   source-to-native field mismatch before cutover.
4. **Cut over** — only after security maturation (M4) is proven; then retire the standalone app
   at home.

## 10. Data model

`solace_bills` (`recurrence_rule`, `calendar_event_id`), `solace_bill_occurrences`,
`solace_paydays`,
`solace_planned_purchases`, `solace_buckets`,
`solace_payday_checklist_items`, `solace_settings`, `solace_finance_categories`,
`solace_account_balance_snapshots`, `solace_payday_checklist_preferences`,
`solace_cycle_closeouts`. Inherit `HouseholdBaseModel`; all financial records use
`sensitivity = financial`.
Bucket records also hold their pay-cycle allocation method/value, rounding, active/order and
remaining-pay cap. Generated checklist rows carry a cycle date and stable source key so refreshes
are idempotent.

## 11. Scope & completion

Native: bills and occurrence history · bills-account forecast · paydays · planned purchases · buckets/set-asides ·
subscriptions represented as recurring bills · payday checklist/preferences · closeout and balance projection · categories and
reports · settings and health checks · CSV/XLSX tools · permission-controlled
Hub/Calendar/notifications · re-auth · audit · imported data.
Complete when only authorised users access Solace through HomeStack, re-auth works, finance
never leaks into unauthorised views, and the standalone app is retired at home. Future:
travel/grocery/asset-purchase budget integration, financial documents and encrypted finance
fields.
For Homestead-linked bills, direct descriptive edit/delete is rejected in Solace so the two
nodes cannot silently diverge; payment/occurrence actions remain Solace-owned.
