# Solace native parity checklist

> Reference implementation: local standalone Project Solace at
> `/home/moose/Documents/project-solace`. This checklist tracks behavioural parity; HomeStack
> keeps shared authentication, permissions, Calendar, Hub, audit and backups rather than
> rebuilding standalone infrastructure.

## Core planning and daily use

- [x] Shared HomeStack login plus password re-authentication for finance.
- [x] Recurring bills with amount, provider/category, first due date and recurrence.
- [x] Independent bill occurrences with upcoming/paid/skipped states and history preservation.
- [x] Monthly bill/income schedule with previous/current/next navigation, calendar/list views,
  totals and occurrence actions.
- [x] Income sources/paydays with recurring schedules and pause/include controls.
- [x] Percentage and fixed household bucket rules, proportional multi-income splitting,
  rounding, remaining-pay caps and ordering.
- [x] Household and per-income pay-cycle transfer plan.
- [x] Cycle-specific, idempotent payday checklist generation and completion.
- [x] Planned purchases with targets, savings progress, priority and dates.
- [x] Subscription tracking and renewal dates.
- [x] Native overview plus permission-controlled Solace Hub widgets.
- [ ] Pay-cycle closeout with notes, closed state and paid/skipped/unpaid reconciliation.
- [ ] Manual bills-account balance snapshots and projected balance after the cycle.
- [ ] Setup/data health checks.

## Management depth

- [x] Bill create/edit/pause/delete UI and protected API.
- [~] Purchase, payday, bucket and subscription CRUD APIs exist; their web screens still need
  the same complete edit/delete affordances as Bills.
- [ ] User-managed bill/purchase categories and category cost overview.
- [ ] Checklist item hiding/preferences.
- [ ] Solace-specific household settings (buffer, budget year, payday-boundary handling,
  currency display). HomeStack appearance/account settings remain shared.
- [ ] Configurable Solace overview layout. Native Hub configuration already covers cross-node
  widgets.

## Operations and data

- [x] Re-authenticated/audited access, central permissions and finance-safe Calendar/Search/Hub.
- [x] Dry-runnable, idempotent standalone SQLite importer for bills, occurrences, subscriptions,
  income, purchases, buckets and the latest checklist cycle.
- [x] HomeStack-wide database/media backup and restore replaces standalone SQLite ZIP backup.
- [x] Central HomeStack audit log replaces the standalone audit table.
- [ ] Solace CSV/XLSX exports and human-readable finance report.
- [ ] Preview/confirm import for ad-hoc bill CSV/XLSX files.
- [ ] Bill due/overdue, payday, subscription and planned-purchase notifications.
- [ ] Finance attachments/documents.

## Cutover gate

The standalone app can be retired only after real household data has been imported, pay-plan
and monthly occurrence totals have been compared for at least one full pay cycle, remaining
management screens are usable on phone and laptop, and export/notification needs are accepted or
implemented.
