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
- [x] Pay-cycle closeout with notes, closed/reopened state, current/next cycle navigation,
  checklist progress and paid/skipped/unpaid reconciliation.
- [x] Manual bills-account balance snapshots, history editing and projected balance after the
  cycle.
- [x] Setup/data health checks with actionable income, bill-date, allocation, overdue and
  balance-age warnings.

## Management depth

- [x] Bill create/edit/pause/delete UI and protected API.
- [x] Purchase, payday, bucket and subscription create/edit/pause/status/delete workflows,
  including purchase completion and one-remainder-bucket enforcement.
- [x] User-managed bill/purchase categories, safe rename/delete handling and category cost
  overview.
- [x] Checklist item hiding/preferences with restoration of generated transfers.
- [x] Solace-specific settings: buffer, budget year, pay-cycle anchor, payday-boundary handling,
  currency display, help tips and reminder window. HomeStack appearance/account settings remain
  shared.
- [x] Native Solace overview plus configurable shared Hub layout replaces the standalone-only
  dashboard widget editor.
- [x] Required fortnightly set-aside and coverage/shortfall breakdown for recurring bills,
  planned purchases and the configured buffer.

## Operations and data

- [x] Re-authenticated/audited access, central permissions and finance-safe Calendar/Search/Hub.
- [x] Dry-runnable, idempotent standalone SQLite importer for settings, categories, recurring
  bills and full occurrence history, income, purchases, buckets, balances, checklist preferences,
  closeouts and the latest checklist cycle. Validated read-only against the live local standalone
  database.
- [x] HomeStack-wide database/media backup and restore replaces standalone SQLite ZIP backup.
- [x] Central HomeStack audit log replaces the standalone audit table.
- [x] Bills, purchases, income and buckets CSV exports; full readable multi-sheet XLSX backup;
  human-readable category report.
- [x] Preview/confirm/cancel import for ad-hoc bill CSV/XLSX files, with per-row errors and file
  limits.
- [x] Idempotent daily bill due/overdue, payday, subscription and planned-purchase reminders.
  Notification text stays generic until password re-authentication.
- [x] Finance documents use HomeStack's shared attachment/document direction; the standalone
  reference app has no bill-attachment workflow to port.

## Cutover gate

Feature parity is complete. The standalone app can be retired only after the production
migrations and real household import have run, pay-plan/monthly totals have been compared for at
least one full pay cycle, and the owner has accepted the phone/laptop workflow. These are cutover
checks rather than remaining implementation gaps.
