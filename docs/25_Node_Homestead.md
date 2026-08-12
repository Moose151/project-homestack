# Node Spec — Homestead

> **Status:** shipped, broad and in daily use. Homestead is the home/property source of truth
> (D21). Current capabilities include property/maintenance/appliances/providers, Costs & cover,
> rooms/room plans, pools & spas, metered utilities, single-entry Solace handoffs, safe product-link
> enrichment and the native interactive floor plan. The proposed Stock & storage / Assets & vehicles
> / Household guide capability consolidation remains a future proposal, not implemented fact.

## 1. Purpose

Homestead answers: **What does our home need, what is in it, who do we call, and what do we want to
change?**

It is intentionally a warm home/property domain rather than a generic asset CMDB.

Homestead owns the physical/property context while related shared/domain systems retain their own
clear ownership:

- finance/payment schedule → Solace;
- general shopping/grocery → Atlas;
- permanent guide/procedure content → Home Wiki unless future capability consolidation is actually
  approved;
- trip planning → Travel;
- medical information → Health;
- shared files → Attachments.

## 2. Property and emergency context

Property records carry the implemented home identity/key-date/details and practical emergency
information such as utility shut-off/equipment locations where configured.

Emergency-safe information can be deliberately kiosk/household visible; account/policy/financial
information remains protected separately.

Do not hardcode this household's exact address/room count/layout into general schema/business rules
(D15).

## 3. Maintenance

Homestead owns recurring and one-off home maintenance.

A MaintenanceTask keeps the semantic next-due date and recurrence. Completion records the action and
advances/clears the next due state according to its recurrence behavior, with Calendar projection
maintained through D7.

Important ownership rule:

- Homestead owns **what work the home needs**;
- Solace owns **the financial bill/occurrence/payment history** where a maintenance cost is tracked.

The approved handoff creates/updates one source-linked financial record without requiring duplicate
manual entry or cross-node model imports.

## 4. Appliances and service providers

Homestead owns home appliance/warranty/manual/serial/context records and the household service
provider directory.

Files/manuals/receipts use the shared attachment capability where stored as files. A URL/reference
field does not bypass the shared security model.

Non-home vehicle/tool/valuables scope remains part of the proposed future Assets & vehicles
capability rather than being mixed into appliance records today.

## 5. Costs & cover / Solace boundary

Homestead can present richer home-specific context for insurance and household service accounts,
while Solace owns financial schedule/payment state.

Examples of Homestead-owned context include policy/account classification, coverage/excess/contact
information and how the cost relates to the home. Examples of Solace-owned facts include amount,
due cycle/recurrence, bill occurrence/payment history and budget treatment.

Protected Costs & cover actions require the appropriate Homestead + Solace permissions and
password re-authentication. These surfaces are not child/kiosk content.

Single-entry handoffs must preserve one owner for each field and reject edits that would silently
diverge linked records.

## 6. Pools & spas

Homestead owns configured pool/spa records, their equipment/context, water-test interpretation and
care/maintenance schedule.

### Water tests

Store the readings actually taken. Interpret in/out-of-range state at read time against current
configured guidance rather than storing a permanent calculated status that becomes wrong when
advice/configuration changes.

Guidance varies by relevant pool/sanitiser/surface characteristics, not by household-specific
hardcoding (D15).

### Care schedule

Pool-care tasks use the ordinary Homestead maintenance/calendar system rather than a parallel pool
task engine.

Starter schedules can be generated idempotently and then edited by the household. Reapplying a
starter/config change must not overwrite custom schedules indiscriminately.

Future schedule changes affect incomplete/future work while completed history remains historical
fact.

## 7. Metered utility usage

Homestead owns **what an arrived utility bill period actually used/cost**, while the corresponding
Solace bill/account owns the recurring future financial schedule.

Usage records can include utility, billing period, usage/unit, total cost, provider, estimated/read
status and notes as implemented.

Derived comparisons use per-day normalized values because billing periods vary in length. Current
views can compare against the previous bill and an approximate year-ago period according to the
implemented matching rules.

Utility usage is household-visible by the current product decision; Costs & cover remains more
protected because it contains account/policy/finance context.

An arrived usage record does not need another Calendar event when its Solace account already owns
the future due date.

## 8. Rooms and areas

Rooms/areas are stable Homestead records with their own names/icons/colours/ordering/detail pages.

They provide the organizing context for:

- room purchases;
- maintenance;
- renovations/upgrades;
- products/references;
- room-specific planning notes/cost estimates.

A room is not merely a drawing polygon: its durable record remains useful even when the floor-plan
presentation changes.

## 9. Room plans

Room plan items combine purchases, maintenance, renovations and upgrades with the implemented
combination of status, priority, assignee, quantity, estimated/actual cost, link and notes.

Totals follow the established rules so planned/in-progress estimates and completed actuals are not
double-counted; archived items remain historical but are excluded from active totals.

Completed/archived records can be restored/reopened according to the service contract rather than
deleted to hide history.

## 10. Interactive floor plan — shipped

The current household has a native responsive SVG representation of the supplied house/property
plan rather than embedding the original listing image.

Current behaviour includes:

- inside-the-house and whole-property views;
- HomeStack light/dark design tokens;
- zoom/fit controls;
- keyboard/pointer selection;
- strong selected-space indication;
- explicit linking of plan slots to existing Room records;
- persistence of the association in room `floorplan_data`;
- linked plan spaces adopting the saved room name/icon/colour;
- tolerant legacy/name suggestions while explicit links win.

The plan is an approximate household navigation/planning surface, not CAD.

A future productized floor-plan **builder/editor** for arbitrary households is separate future work.

## 11. Room products and safe link import — shipped

Homestead room product/planning flows reuse the shared safe Link Import service rather than
implement a Homestead scraper.

A pasted product URL can preview supported metadata such as title/retailer/price/image. The user
reviews/edits the result before it becomes confirmed HomeStack data.

Important rules:

- confirmed/manual HomeStack fields are the saved source of truth;
- bot challenge/error page titles are rejected rather than stored as product names;
- the importer fills blank/confirmable information and does not overwrite existing user-confirmed
  values with poor external metadata;
- confirmed images may be cached locally according to the shared link-import policy;
- optional price watches observe/notify without silently rewriting the saved planned cost.

## 12. Corners / People projection — shipped baseline

Assigned/visible Homestead room plan items/products can appear in the appropriate Person's Corner
through the shared projection contract. Corners do not move or copy ownership away from Homestead.

Suggestions/reactions remain permission-aware and source-linked.

## 13. Permissions

General Homestead records follow `homestead.*` permissions plus visibility filtering.

Sensitive/protected areas add stronger gates, especially:

- Costs & cover/account/policy data;
- Solace-linked finance actions;
- sensitive attachments/identifiers.

Children/users may see ordinary household home/utility/planning information where permitted but do
not gain finance/account access simply because it is presented inside Homestead.

## 14. Hub / Calendar / Notifications

Homestead may contribute permission-aware summaries such as:

- maintenance due/overdue;
- warranty expiry;
- active room/home improvements;
- pool-care work;
- relevant household/home attention items.

Calendar mirrors Homestead-owned dates through D7. Solace-owned financial due dates remain Solace
Calendar projections.

Notifications use the shared notification/Web Push system. Sensitive account/policy/financial
content must not leak into ordinary push payloads.

## 15. Search and attachments

Search covers permitted Homestead records/room/product context according to current selectors.
Protected finance/sensitive fields are filtered by source permissions before snippets.

Files use shared Attachments; manual/external product URLs use the safe link-import boundary where
applicable.

## 16. Capability consolidation proposal — not yet implemented

`31_Core_Manage_HomeStack.md` proposes reducing future top-level navigation by presenting these as
optional Homestead capabilities:

- **Stock & storage** (planned Inventory scope);
- **Assets & vehicles** (remaining non-home Assets scope);
- **Household guide** (possible future presentation of Home Wiki content).

This remains a proposal. Do not claim those capabilities exist or migrate/delete existing Home Wiki
data merely to simplify navigation.

If implemented later, hiding a capability must preserve data/permissions and re-enabling it must
restore the prior records cleanly.

## 17. Heavy project boundary

Homestead already owns home improvements/room plans. Do not create a Projects node for home work it
can already represent.

A future top-level Projects domain is justified only if real non-home/cross-domain work needs
substantially richer boards/dependencies/templates/budget/history than Homestead/Travel/Atlas can
provide.

## 18. Data ownership

Exact schema is defined by current Django models/migrations. Homestead owns the implemented
families for property, maintenance, appliances/providers, home insurance/cost context, pools/water
tests, utilities, rooms/room plans/products and floor-plan association data.

Solace remains the owner of financial bill/payment records; Attachments and Link Import remain
shared core capabilities.

## 19. Completion state

Homestead's broad current baseline is shipped and used. Future work should be driven by lived home
use and productization needs rather than by adding every conceivable property-management feature.

Likely future directions include the optional capability consolidation, deeper document/warranty
linkage, portable floor-plan onboarding/builder tooling and measured refinements to maintenance/
pool/utility workflows.