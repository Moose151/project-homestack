# Node Spec — Solace / Money (native)

> **Status:** shipped, deployed and in daily household use. Solace is HomeStack's native sensitive
> finance domain (D13/D14), not an external integration. The live household chose fresh manual
> bill entry instead of importing the standalone Solace database; import/verify tooling remains
> available but is not an outstanding cutover task.

## 1. Purpose

Solace answers the practical household finance questions:

- What bills and required transfers are coming up?
- What needs to happen in the current/next pay cycle?
- What money must remain set aside?
- What planned purchases are coming?
- Is the bills account projected to stay safe?

It is intentionally sensitive. Finance must not leak through Hub, Calendar, Search, Corners,
notifications, kiosk or direct-ID requests to an unauthorised User.

## 2. Ownership boundaries

**Solace owns:** bills and bill occurrences, pay-cycle planning, bucket/allocation rules, planned
purchases, finance categories/settings, account-balance/forecast state and other implemented Money
records.

**Belongs elsewhere:**

- shopping/grocery items → Atlas;
- recipes/meal plans → future Hearth;
- property/room/appliance/policy descriptive context → Homestead;
- travel itinerary → Travel;
- documents → shared Attachments linked to the owning record;
- child tasks/rewards → Meridian.

Subscriptions are represented within the current Bill model/workflow rather than maintained as a
separate parallel subscriptions product surface.

## 3. Users and permissions

- Admin has finance access subject to the sensitive re-auth gate.
- Manager may be explicitly granted Money access.
- Ordinary Users/children do not see Money by default.
- Node access and per-record visibility are backend enforced.
- Sensitive access/elevation and other protected actions are audited.

Re-authentication uses the adult password, not the PIN.

## 4. Current core capability

The native implementation includes the shipped combination of:

- recurring and one-off bills;
- independent due-date occurrences that can be paid/restored/skipped without changing the bill
  recurrence definition;
- paydays/pay-cycle planning;
- percentage/fixed bucket/allocation logic;
- payday checklist generation/preferences;
- planned purchases;
- current/next cycle closeout and set-aside/shortfall views;
- account-balance snapshots/health;
- dated bills-account forecast and safe-to-withdraw calculation;
- categories/reports/settings;
- CSV/XLSX export and reviewed import tools;
- permission-aware Search/Hub/Calendar/notifications;
- Homestead single-entry financial handoffs where ownership stays explicit.

Treat the current code/tests as authoritative for exact UI/model fields rather than reviving old
standalone-Solace terminology.

## 5. Bill occurrence/timezone rules

The owning bill stores its recurrence/source configuration. Due occurrences are reconciled over
bounded windows and represent payment/skip state independently from the recurring definition.

Date/pay-cycle math uses the **household timezone**, not process-global UTC assumptions. This is a
live-use regression boundary: a bill due "today" must be classified according to the household's
local date even though the Docker process may run with UTC as its active timezone.

Performance-sensitive views should avoid repeatedly reconciling the same bill/window within one
request; use the established request-scoped reconciliation behavior rather than reintroducing
multiple overlapping occurrence rebuilds.

## 6. Bills-account forecast

The forecast projects expected Bills-bucket transfers against bill occurrences over a 1–24 month
window. **A bill leaves the bills account when `paid_from_bills_account` is true.** This is
independent of `include_in_set_aside`, which only controls the saving target in pay-cycle planning.
A mortgage paid by direct debit still counts even when set-aside planning is disabled.

Migration `solace.0012` adds the payment-account flag, defaulting existing and new bills to true.
An old set-aside preference is not evidence that a bill is paid elsewhere. Households should mark
bills paid from other accounts explicitly; nothing changes their set-aside preferences or payment
history. The flag is included in bill editing and readable CSV/XLSX export/import.

The forecast returns `bill_coverage` for every bill the reader can access: payment count and total,
or a reason for exclusion (paid elsewhere, paused, missing date, or no payments in the window).
Skipped occurrences are excluded, recurrence end dates are respected, and overdue unpaid
occurrences are carried to the opening day if their due date precedes it. Marking an overdue
payment as paid updates its treatment. No private bill names may leak through this explanation.

Balance snapshots mean **end of the recorded day**. Projection starts the following day, including
intervening cash flow when a snapshot is older than today. Without a snapshot it starts today and
still shows bills, transfers and the required opening balance; unknown balances remain unknown.
Paid occurrences use `paid_at` (due date for legacy rows with no payment timestamp). Payments
already included in the opening balance are not deducted again, including early-paid bills with
future due dates. Pausing a schedule stops future bills but does not erase payments made since
the snapshot. Dates and transfer cycles use the household timezone.

`first_shortfall_date` is separate from `lowest_balance_date`. The UI shows the top-up required,
projected low point, and the assumptions behind any headroom. Same-day transfers are assumed to
arrive before payments; the chart shows end-of-day balances. Missing due dates, overdue debts,
no scheduled transfers and balances over 14 days old produce visible warnings. Expected transfers
are plans, not reconciled bank transactions; updating the balance accounts for other bank activity.

### Everyday Money workflow

- **Overview:** bills-account position, current-cycle payments, Add bill, Update account balance,
  and setup shortcuts for income / bills / bills transfers.
- **Bills:** due-date ordered bill register, upcoming unpaid payments and calendar. Search and
  category/status filters affect the list; they do not change household planning totals.
- **Payday plan:** transfers, savings/buckets, income, purchases and an accessible checklist on
  both phone and desktop. Generating a checklist opens it directly. A phone section picker keeps
  these destinations readable.
- **Bills account:** forecast, interactive balance chart, coverage review with links to the bills,
  dated cash flow, and existing closeout/history/annual reports. A closing balance can be recorded
  here without a detour through settings; failed saves retain the entered values.
- **Settings:** household finance preferences, categories, balance history and import/export.

Existing `tab`/`section` routes and global/Home search links continue to work. Search results are
kept separate from the full household datasets, so searching does not change the forecast or the
allocation rules used when creating/editing a bucket. The cycle-end label describes the cycle,
rather than claiming it is the next actual payday.

**A bucket funds the bills account when its `purpose` is `bills`** — the value the bucket form
sets. Both the forecast and the pay-cycle plan's set-aside total previously decided this by looking
for the substring "bill" in a free-text `category` field that the form never populated, so both
came out as zero: the forecast showed bills leaving the account with no pay arriving, and the plan
reported a shortfall equal to the entire required amount however the household had set its buckets
up. `category` has been removed from `BudgetBucket` (migration `solace.0011`, which first promotes
any bucket whose old category said "bill" to `purpose=bills`). The plan's set-aside total counts
`bills` and `purchases`.

It can expose the implemented combination of:

- running projected balance;
- lowest projected balance;
- first risk date;
- required opening balance;
- configured buffer;
- safe-to-withdraw figure.

A balance snapshot has a precise date/time interpretation. Stale balance information should produce
an explicit health warning rather than silently presenting the projection as current fact.

## 7. Homestead handoff

HomeStack keeps one clear owner for descriptive property context and one clear owner for finance.

Examples:

- a Solace bill classified as a home service/cost may create or claim the corresponding richer
  Homestead descriptive record through the approved event/service boundary;
- a Homestead maintenance cost request can create/update one source-linked Solace financial bill;
- Homestead edits descriptive context while Solace owns due occurrences/payment history;
- direct edits that would make the linked records silently diverge are rejected or routed through
  the owning side.

No cross-node model imports are introduced to make this work (D4).

## 8. Hub / Calendar / Notifications

Only authorised Users may receive Money-derived summaries.

Possible/implemented projections include bills due/overdue, payday/cycle actions, planned purchases,
finance health and related reminders.

Calendar rows are source-linked projections and remain filtered by finance permissions/sensitivity.
Notification content, especially phone push, must be sparse enough that lock screens do not reveal
bill names, amounts or account information before the app re-checks access.

The scheduled Solace command remains idempotent/catch-up-safe and should use household-local date
semantics.

## 9. Search and kiosk

Search is finance-permission filtered before snippets are produced.

Solace has no ordinary child kiosk surface. Any adult sensitive access on a shared kiosk remains
password-re-authenticated with the shorter elevation/session behavior.

## 10. Legacy standalone Solace / import tooling (D14)

The standalone repository remains a historical/behaviour reference and the native importer remains
useful tooling.

The original migration approach was:

1. rebuild native HomeStack models/services/UI around shared platform services;
2. reuse proven recurrence/budget/pay-cycle behavior;
3. optionally dry-run/import/verify legacy data;
4. cut household use over to native HomeStack.

For the current live household, step 3 was intentionally skipped: bills were entered fresh into
HomeStack. Therefore **"run the Solace importer" is not an active deployment task or completion
gate**.

Keep the importer tested/idempotent enough for future migration scenarios, but do not make current
Money behavior depend on the legacy database/app being present.

## 11. Data ownership

Exact schema is defined by current Django models/migrations. Major native data families include the
implemented equivalents of:

- bills and bill occurrences;
- paydays/pay-cycle state;
- planned purchases;
- buckets/allocation settings;
- payday checklist rows/preferences;
- finance categories/settings;
- account-balance snapshots;
- cycle closeouts.

All financial records use the established sensitive/financial permission boundary.

## 12. Completion state and future work

The native Solace household cutover is **complete**: it is deployed, permission/re-auth protected
and used with real household bills.

Future enhancements are feature work rather than migration completion, for example:

- richer exports/reporting where useful;
- tighter but ownership-safe Travel/Hearth/vehicle planning links;
- encrypted finance fields only if the threat model justifies the operational complexity;
- further measured performance work if live request timing identifies another real bottleneck.

Any future change must preserve the rule that unauthorised derived surfaces reveal no meaningful
finance detail.