# Solace native parity checklist

> Reference implementation: local standalone Project Solace at
> `/home/instructor/Documents/new/project-solace`. This checklist tracks behavioural parity;
> HomeStack keeps shared authentication, permissions, Calendar, Hub, audit and backups rather
> than rebuilding standalone infrastructure.
>
> **This document claimed complete parity before a line-by-line re-read of the standalone code on
> 2026-08-10 (v0.28.0) found three features that had never been ported.** Two are now done; the
> rest are listed under "Found missing" below. Tick items here only against the standalone source,
> not against a summary of it.

## Core planning and daily use

- [x] Shared HomeStack login plus password re-authentication for finance.
- [x] Recurring bills with amount, provider/category, first due date and recurrence.
- [x] Bill autopay and stop-after metadata; category/status filters and sorting; detail metrics
  with 12 upcoming and 12 historical occurrences; safe future/all-unpaid edit scope.
- [x] Independent bill occurrences with upcoming/paid/skipped states and history preservation.
- [x] Monthly bill/income schedule with previous/current/next navigation, calendar/list views,
  totals and occurrence actions.
- [x] Income sources/paydays with recurring schedules and pause/include controls.
- [x] Known income anchor plus calculated upcoming payday, with current/next Pay plan navigation.
- [x] Percentage and fixed household bucket rules, proportional multi-income splitting,
  rounding, remaining-pay caps and ordering. Only the first cap-to-remaining bucket may cap,
  matching the reference engine's defensive behaviour.
- [x] Household and per-income pay-cycle transfer plan.
- [x] **Individual vs shared income (v0.28.0).** Shared income belongs to the household: it is
  excluded from the per-person contribution breakdown and applied to buckets after the personal
  splits, so a shared deposit cannot inflate anybody's share.
- [x] **Shared-income allocation modes (v0.28.0).** `standard` flows through the usual bucket
  rules; `lump` sends the whole amount to one nominated bucket; `custom` applies each line's
  percentage in order with one line taking the remainder. Without a remainder line the unallocated
  amount stays in the account rather than being invented into a bucket.
- [x] **Per-person contribution breakdown (v0.28.0).** Income carries `owner_name`, so the pay
  plan reports what each person contributed and where it went. The importer previously flattened
  the owner into the income title, losing the grouping entirely.
- [x] Cycle-specific, idempotent payday checklist generation and completion, including
  current/next navigation and confirm-income/review-bills/record-balance workflow steps.
- [x] Planned purchases with targets, savings progress, priority, dates and capped quick-add.
- [x] Subscription tracking and renewal dates.
- [x] Native overview plus permission-controlled Solace Hub widgets.
- [x] Pay-cycle closeout with notes, closed/reopened state, current/next cycle navigation,
  checklist progress and paid/skipped/unpaid reconciliation.
- [x] Manual bills-account balance snapshots, history editing and projected balance after the
  cycle.
- [x] Auditable 3–24 month bills-account forecast combining expected Bills-bucket transfers,
  included bill occurrences and active subscriptions; lowest balance, first risk date,
  shortfall, required opening balance, bills-only surplus and buffer-preserving withdrawal.
- [x] Setup/data health checks with actionable income, bill-date, allocation, overdue and
  balance-age warnings.

## Management depth

- [x] Bill create/edit/pause/delete UI and protected API.
- [x] Purchase, payday, bucket and subscription create/edit/pause/status/delete workflows,
  including purchase completion and one-remainder-bucket enforcement.
- [x] User-managed bill/purchase categories, safe rename/delete handling and filterable weekly,
  fortnightly, monthly and yearly category cost overview.
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
  closeouts and the latest checklist cycle. A read-only `--verify` mode checks the imported
  natural-key records and financially significant fields against the standalone database,
  reporting actionable drift. Validated read-only against the live local standalone database.
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

## Found missing on re-reading the standalone source (2026-08-10)

- [x] Individual vs shared income, allocation modes and the per-person breakdown (v0.28.0).
- [x] **Cycle history (v0.28.1).** Every closed-out cycle, newest first, with what was paid,
  skipped and left outstanding in each. The per-cycle figures are recomputed from the occurrences
  in that window rather than stored, so correcting a bill later corrects the history too.
- [x] **Annual summary (v0.28.1).** A calendar or financial year (1 July – 30 June) of bill
  occurrences grouped by category and then by bill, both ordered by cost, with paid and
  outstanding totals. Uncategorised bills are still counted.
- [x] **Purchase completion (v0.28.1).** Marking a purchase bought now raises its saved amount to
  the target, so a purchase that reached the shop part-saved stops reading as short. A balance
  already above the target is left alone.

With these, no behavioural gap against the standalone app is known. Anything found from here
should be added to this list rather than assumed absent by omission.

## Cutover gate

Feature parity is complete apart from the items listed above. The standalone app can be retired
only after the production
migrations and real household import have run, `import_solace --verify` passes, pay-plan/monthly
totals have been compared for at least one full pay cycle, and the owner has accepted the
phone/laptop workflow. These are cutover checks rather than remaining implementation gaps.
