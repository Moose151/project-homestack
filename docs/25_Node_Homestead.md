# Node Spec — Homestead

> Canonical. Shipped V1 (2026-07-21, v0.10.0). Global rules from `00_README_and_Changelog.md`
> apply. See **D21** for why this node exists and how it relates to Assets / Projects / Solace.

## 1. Purpose & philosophy

The household's **home/property hub**. Answers: *"What does our home need, what's in it, who do
we call, and what do we want to improve?"* Built when the owner bought a house (2026-07-21). Folds
the **home scope of the planned Assets node** into one warm, house-focused surface, and is designed
to become an **aggregating hub** — surfacing house-relevant slices of Solace (bills/rates) and
Projects (renovations) once those exist, always via the events bus (D4).

## 2. Belongs / does not belong

**Belongs:** the property record + key dates (purchase/move-in), practical emergency info (water
stopcock, gas shut-off, consumer unit, boiler location), recurring/one-off **maintenance** and
renewals, **appliances** + warranties + manuals + serials, a **service-provider** directory, and a
lightweight **improvements** list.
**Not:** budgets/bills/mortgage → **Solace** (Homestead surfaces them later, read-only); heavyweight
renovations with task boards → **Projects** (an Improvement can link via `project_ref`); how-to
guides & manuals text → **Home Wiki**; simple to-do lists → **Atlas**; vehicles/tools/non-home
assets → a future **Assets** node if ever built.

## 3. Key features

**Property** — name, type, tenure, address, purchase/move-in dates, year built, notes, emergency
info (water/gas/electric/boiler locations, kiosk-safe). Usually one row; multiple allowed.
**Maintenance** — title, category, `next_due_at` (source of truth), `recurrence_rule` (RRULE, D8),
`last_done_at`, optional linked appliance/provider, assignee. **Mark done → advances to the next
occurrence** (dateutil), clearing the reminder when non-recurring. The Pets-treatment pattern.
**Appliances** — name, category, brand/model/serial, room, purchase date, warranty expiry
(countdown), warranty provider, manual link, notes.
**Service providers** — name, trade, company, phone/email/website, last used, notes.
**Improvements** — title, status (idea→planned→in-progress→on-hold→done/cancelled), priority, room,
optional target date (→ Calendar), assignee, `project_ref` (dormant link to a future Project).

## 4. Permissions

`homestead.view` (all roles) · `homestead.create`/`homestead.edit` (admin/manager/user) ·
`homestead.delete` (admin/manager). Finer visibility (private/sensitive records hidden from other
users/children) via the central resolver + `apply_visibility` (D10), not extra codes.

## 5. Hub / Calendar / Notifications

Widgets (hub mig `0011`): **home maintenance** (due/overdue), **warranties expiring**, **home
improvements** (active). Calendar (via helper, D7): maintenance `next_due_at` and open improvement
`target_date`, `source_node = "homestead"`; recurring maintenance carries an RRULE (D8). Kiosk off
for now. Notifications: assignment/overdue reminders are a later slice.

## 6. Events (signals)

Publishes (D4): `homestead.property_created`, `homestead.maintenance_completed`,
`homestead.appliance_added`, `homestead.improvement_created`, `homestead.improvement_completed`.
**Designed to consume** (when the source nodes exist): `solace_*` (bills/rates → Overview panel)
and `project_*` (house projects → linked from Improvements) — via a handler keeping lightweight
references and deep-links, never importing another node's models.

## 7. Search / Kiosk

FTS `search_homestead` (Postgres SearchVector + SQLite icontains fallback, D9) over appliances
(name/brand/model/serial/room/notes), maintenance (title/notes), providers (name/company/notes),
and improvements (title/description/room/notes) — permission-filtered. Not a primary kiosk node;
emergency info is kiosk-safe for a future safe view.

## 8. Data model

`homestead` app. `Property`, `ServiceProvider`, `Appliance`, `MaintenanceTask` (CalendarSyncMixin),
`Improvement` (CalendarSyncMixin). All inherit `HouseholdBaseModel`. No per-item `property` FK in V1
(single home; avoids the `property`/`@property` clash and is YAGNI). No cost fields (money → Solace).
`Improvement.project_ref` is the forward hook to the Projects node.

## 9. Scope & completion

V1 (done): property record + emergency info · maintenance with recurrence + complete-advances +
calendar sync · appliances + warranties · service-provider directory · improvements · FTS · three
Hub widgets · `homestead.*` permissions · node catalogue (disabled by default) · 28 tests. Frontend:
`/homestead` route (node-gated) + 5 tabs (Overview/Maintenance/Appliances/Improvements/Contacts) +
search + Hub renderers. Future: Solace bills/rates panel + Projects linking (the aggregating-hub
vision), meter readings, rooms as structured records, document attachments, seasonal maintenance
templates, kiosk safe view, assignment/overdue notifications.
