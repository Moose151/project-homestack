# Node Spec — Homestead

> Canonical. Shipped V1 (2026-07-21, v0.10.0); costs & cover added in v0.11.2;
> room/area planning added in v0.18.0; single-entry Solace handoff added in v0.19.2;
> maintenance-to-Solace cost creation added in v0.19.3; pools & spas added in v0.26.0;
> metered utility usage added in v0.29.0; Solace-only bill ownership adopted in v0.29.6.
> Global rules from `00_README_and_Changelog.md`
> apply. See **D21** for why this node exists and how it relates to Assets / Projects / Solace.

## 1. Purpose & philosophy

The household's **home/property hub**. Answers: *"What does our home need, what's in it, who do
we call, and what do we want to improve?"* Built when the owner bought a house (2026-07-21). Folds
the **home scope of the planned Assets node** into one warm, house-focused surface, and is designed
to be an **aggregating hub** — home policies/accounts are displayed here while every financial
schedule is managed in Solace; future renovations come from Projects. Cross-node flow always
uses the events bus (D4).

## 2. Belongs / does not belong

**Belongs:** the property record + key dates (purchase/move-in), practical emergency info (water
stopcock, gas shut-off, consumer unit, boiler location), recurring/one-off **maintenance** and
renewals, **appliances** + warranties + manuals + serials, a **service-provider** directory, and a
lightweight **improvements** list. Also belongs: home insurance policy details and home service
accounts/costs (rates, water, gas, electricity, mortgage/rent, strata, waste and internet), plus
structured rooms/areas and their wanted purchases, maintenance, renovations and upgrades, and
**metered usage** — what each water/electricity/gas bill covered, used and cost.
**Not:** whole-house budgeting/paydays/savings → **Solace**; heavyweight
renovations with task boards → **Projects** (an Improvement can link via `project_ref`); how-to
guides & manuals text → **Home Wiki**; simple to-do lists → **Atlas**; vehicles/tools/non-home
assets → a future **Assets** node if ever built.

## 3. Key features

**Property** — name, type, tenure, address, purchase/move-in dates, year built, notes, emergency
info (water/gas/electric/boiler locations, kiosk-safe). Usually one row; multiple allowed.
**Maintenance** — title, category, `next_due_at` (source of truth), `recurrence_rule` (RRULE, D8),
`last_done_at`, optional linked appliance/provider, assignee. **Mark done → advances to the next
occurrence** (dateutil), clearing the reminder when non-recurring. The Pets-treatment pattern.
Paid maintenance can start on either side without re-entry: a Solace bill can be organised here,
or an existing Homestead task can use **Track cost** to create its one protected Solace bill.
Homestead owns task details while Solace retains amount, schedule and payment history.
**Appliances** — name, category, brand/model/serial, room, purchase date, warranty expiry
(countdown), warranty provider, manual link, notes.
**Service providers** — name, trade, company, phone/email/website, last used, notes.
**Improvements** — title, status (idea→planned→in-progress→on-hold→done/cancelled), priority, room,
optional target date (→ Calendar), assignee, `project_ref` (dormant link to a future Project).
**Insurance** — Solace owns name, provider, premium/cycle, renewal, recurrence, active state and
finance notes. Homestead displays those values and owns only home-specific policy type/number,
excesses, coverage summary and claims contact/portal.
**Household costs** — Solace owns rates, water, gas, electricity, mortgage/rent, strata/body
corporate, waste and internet bill names, providers, amounts, cycles, due dates, recurrence and
active state. Homestead displays linked bills and owns only the home classification/account number.
**Pools & spas** — a pool, spa, swim spa or plunge pool, with how it is sanitised (saltwater,
manually chlorinated, mineral, bromine), surface, filter type, volume and equipment notes.
Two things follow from those choices rather than being asked for again:

- **Target water bands.** `pool_care.py` holds the widely published domestic-pool ranges and
  varies them by sanitiser and surface — a salt pool is held to a higher stabiliser band because
  the cell trickles chlorine in all day, fibreglass and vinyl need less calcium than concrete, and
  a manually chlorinated pool is never asked for a salt reading. A `WaterTest` records whichever
  readings were actually taken; whether each is in range is computed at read time against the
  current targets, never stored, so corrected guidance applies to old readings too. Every reading
  carries what it is for and, when out of band, what to do about it — the node is meant to be
  usable by a household that has never looked after a pool.
- **A starter care schedule.** Adding a pool creates the usual jobs (skim, test, brush, vacuum,
  empty baskets, monthly full test, filter clean, salt-cell inspection, annual service), staggered
  so they do not all land on day one. These are ordinary `MaintenanceTask` rows carrying
  `category="pool"` and a `pool` FK, so they recur (D8), reach the Calendar (D7), complete and
  advance, and appear in Maintenance and the Hub exactly like any other home job — the link exists
  so the pool screen can claim its own jobs, not to fork the behaviour. Re-applying the schedule is
  idempotent by title, so switching to a salt cell adds only the job that switch introduces and
  never overwrites a job the household has edited.

Kept general (D15): the bands and the schedule come from how the pool is built and sanitised, not
from whose pool it is.

**Utility usage** — one `UtilityBill` per arrived bill: which utility, the period it covers, how
much was used and in what unit, what it cost in total, and whether the meter was read or
estimated. The linked Solace Bill owns the recurring account and when the next bill is due; this
usage record owns what actually happened.

Everything derived is calculated at read time and per day — `days` (both end dates included),
`daily_usage`, `daily_cost` and the effective `unit_cost`. Billing periods are not equal lengths,
so a 92-day quarter next to an 88-day one would otherwise look 5% worse before anyone turned
anything on. The usage endpoint returns one series per utility, oldest period first, with totals,
per-day averages, and two comparisons: **vs the previous bill** and **vs a year ago** — matched to
the closest period start within 45 days of a year earlier, because utilities are seasonal and
billing dates drift. Mixed units inside one utility take the newest bill's unit for the series so a
chart never adds kL to litres.

Household-visible by default (owner, 2026-08-10): usage is something the whole house should be
able to look at, so this surface has **no password gate** — unlike Costs & cover next door, which
holds account and policy numbers. Nothing is written to the Calendar: a bill that has arrived is
not an appointment, and its account already owns the due date (D7).

**Rooms & areas** — named interior, outdoor, utility, storage or other spaces. Every room is a
link to a stable dedicated page (and therefore a future floor-plan destination), with icon,
colour, ordering, description and reserved `floorplan_data` metadata.
**Room plans** — one unified list of purchases, maintenance, renovations and upgrades per room,
including status (planned/in progress/completed/archived), priority, assignee, quantity,
estimated unit cost, optional actual total cost, reference link and notes. Active items are
grouped by type; completed and archived records stay visible and can be restored. Room and
household totals count active estimates plus completed actual cost (falling back to estimate)
and exclude archived items.

## 4. Permissions

`homestead.view` (all roles) · `homestead.create`/`homestead.edit` (admin/manager/user) ·
`homestead.delete` (admin/manager). Finer visibility (private/sensitive records hidden from other
users/children) via the central resolver + `apply_visibility` (D10), not extra codes.
The **Costs & cover** endpoints and maintenance **Track cost** action additionally require
`solace.*` permission, password re-auth and audit every access. They are therefore admin-only by
default and never kiosk-visible.

## 5. Hub / Calendar / Notifications

Widgets (hub mig `0011`): **home maintenance** (due/overdue), **warranties expiring**, **home
improvements** (active). Calendar (via helper, D7): maintenance `next_due_at` and open improvement
`target_date`, `source_node = "homestead"`; recurring maintenance carries an RRULE (D8). Kiosk off
for now. Insurance renewals and household-cost due dates create **Solace** financial Calendar
events only, avoiding duplicate Homestead events and retaining Solace re-auth filtering.
Solace-funded maintenance follows the same rule: it appears in the Maintenance workspace but
does not create a second Calendar row.
Notifications: assignment/overdue reminders are a later slice.

## 6. Events (signals)

Publishes (D4): `homestead.property_created`, `homestead.maintenance_completed`,
`homestead.appliance_added`, `homestead.improvement_created`, `homestead.improvement_completed`,
`homestead.room_created`, `homestead.room_item_created`, `homestead.room_item_completed`,
`homestead.maintenance_cost_requested`, `homestead.pool_saved`, `homestead.pool_deleted`,
`homestead.water_test_logged` and `homestead.utility_bill_logged`.
Solace publishes `solace.bill_saved`/`solace.bill_deleted`; Homestead refreshes or removes its
linked Costs & cover display record and stores only that lightweight bill reference. Future
`project_*` events link house projects to Improvements. Nodes never import each other's models.
Solace can also publish `solace.homestead_record_requested` for an explicitly classified bill;
Homestead idempotently creates the correct policy, cost or maintenance record and publishes the
lightweight link back. Linked maintenance save/delete events keep that same bill aligned; repeated
cost requests update the existing source-linked bill instead of creating another.

## 7. Search / Kiosk

FTS `search_homestead` (Postgres SearchVector + SQLite icontains fallback, D9) over appliances
(name/brand/model/serial/room/notes), maintenance (title/notes), providers (name/company/notes),
improvements (title/description/room/notes), rooms (name/description), and room plan items
(title/description/notes) — permission-filtered. Room and item results deep-link to the dedicated
room page. Not a primary kiosk node;
emergency info is kiosk-safe for a future safe view.
Policy/account-number search is available only inside the unlocked Costs & cover surface and is
kept out of the ordinary Homestead search response.

## 8. Data model

`homestead` app. `Property`, `ServiceProvider`, `Appliance`, `MaintenanceTask` (CalendarSyncMixin),
`Improvement` (CalendarSyncMixin), `RoomArea`, `RoomPlanItem`, `InsurancePolicy`, `HouseholdCost`,
`Pool`, `WaterTest`, `UtilityBill`. All inherit
`HouseholdBaseModel`. No per-item `property` FK in V1 (single home; avoids the
`property`/`@property` clash and is YAGNI). `InsurancePolicy`/`HouseholdCost` own only home-specific
metadata and keep `solace_bill_ref`; the linked `Solace.Bill` owns every financial field, its
occurrences/payment history and the financial Calendar mirror.
Solace-funded `MaintenanceTask` rows also keep only `solace_bill_ref` and suppress their ordinary
Homestead Calendar mirror so the shared timeline remains single-entry.
`Improvement.project_ref` is the forward hook to the Projects node.

## 9. Scope & completion

V1 (done): property record + emergency info · maintenance with recurrence + complete-advances +
calendar sync · appliances + warranties · service-provider directory · improvements · structured
room/area plans and costs · pools/spas with target water bands, water-test history and a starter
care schedule · metered utility usage with per-day comparison charts · FTS · three Hub widgets · `homestead.*` permissions · node catalogue
(disabled by default). Frontend: `/homestead` route (node-gated) + 7 tabs
(Overview/Rooms/Maintenance/Appliances/Pool & spa/Power & water/Improvements/Contacts/
Costs & cover), dedicated
`/homestead/rooms/:roomId` pages, search and Hub renderers.
Costs & cover includes annualised summaries, protected search, read-through bill cards and editing
for home-specific policy/account metadata. Bill CRUD, payment history and autopay live in Solace.
Solace bill creation/edit can hand home insurance, household services and paid maintenance into
these workspaces without re-entry; Homestead maintenance can create the same protected financial
record in the other direction. Linked cards deep-link between their owning workspaces.
Future: clickable floor-plan rendering, Projects linking, meter readings entered as counter
values (usage is entered directly today), tying a utility bill to its `HouseholdCost` account,
utility usage in FTS and a Hub widget, document attachments,
seasonal maintenance templates, kiosk safe view, assignment/overdue notifications.
