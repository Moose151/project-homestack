# Node Spec — Atlas

> **Status:** shipped and in daily use. Atlas is HomeStack's general household organisation domain
> and the owner of ordinary household lists, including the dedicated Grocery and Shopping surfaces.
> Global rules D1–D24 apply.

## 1. Purpose

Atlas is the place for everyday household information that needs to be written down, checked off,
assigned or remembered but does not justify a dedicated domain.

It answers: **What do we need to remember, do, buy or organise?**

Atlas must remain lightweight. It is not the finance system, reward economy, recipe database,
property system or large-project manager.

## 2. What belongs in Atlas

Examples:

- quick notes;
- ordinary household to-dos/checklists;
- Grocery list;
- Shopping list for non-room/non-personal purchases;
- household reminders;
- lightweight planning/packing lists not owned by Travel;
- external People/birthday contacts;
- Agenda / permitted Calendar projection;
- quick capture from Hub/mobile.

## 3. What belongs elsewhere

- rewarded chores/tasks/points → Meridian;
- bills/budgets/financial purchases → Solace;
- recipes/meal plans → Hearth;
- property/room plans/products → Homestead;
- trip itinerary/packing tied to a Trip → Travel;
- durable household reference/procedures → Home Wiki;
- medical information → Health;
- complex cross-domain project planning → only a future Projects domain if real use justifies it.

## 4. Core record types

### Notes

Household/private notes with the implemented text/visibility/search/attachment behavior.
Rich Markdown/templates remain optional future enhancements rather than requirements for basic
capture.

### General lists / to-dos / checklists

Lists/items support the implemented combination of text, completion state, People assignment,
due-date/Calendar sync, ordering and relevant visibility.

Completion actors are Users; assignees/subjects are People (D12).

### Personal lists / wishes

Personal Atlas lists can belong to a Person and surface in Corners. Household members suggest
changes/items through the bounded suggestion flow rather than silently rewriting somebody else's
personal list. Meridian remains owner of the points/reward wishlist.

## 5. Grocery — shipped dedicated surface

Grocery is deliberately simple and fast for ordinary household shopping.

The normal grocery item emphasizes:

- item/name;
- quantity;
- optional assignee/shopper as implemented;
- completion/tick state.

Do not turn Grocery into a product catalogue or pantry database. Future Hearth meal planning should
**send missing ingredients into this existing Atlas Grocery list** rather than create a second
grocery source of truth.

If future Inventory/Stock exists, it may suggest grocery needs but Atlas still owns the shopping
list itself.

## 6. Shopping — shipped dedicated surface

Shopping is for ordinary household products that are neither:

- a Homestead room/project purchase; nor
- a Person-specific Corner wish; nor
- a Solace financial/budget record.

The shipped Shopping surface supports the richer product flow, including the implemented
combination of:

- item/product name;
- quantity;
- priority (low/medium/high);
- safe paste-a-link preview/fill through the shared link-import boundary;
- confirmed product/supplier/price/image fields where available;
- optional shared price watch;
- completion state.

The importer fills blank/confirmable fields and must not overwrite user-confirmed data with bot
challenge/error-page content. Price watches notify about meaningful changes without silently
rewriting the saved confirmed price.

## 7. Reminders and dated work

Atlas reminders and due-dated list/checklist items remain Atlas-owned. Their dates sync to Calendar
through the shared scheduling helper (D7).

There is no separate "show on Calendar" copy. Changing/clearing the Atlas due date updates/removes
the projection.

## 8. Agenda / Appointments & events

**Agenda** is an actionable permission-filtered projection of Calendar/source-owned work. It does
not create duplicate Atlas records for Calendar-owned appointments or other nodes' records.

**Appointments & events** is the browse/manage projection for standalone Calendar records with the
implemented type/person/date filtering.

Rules:

- standalone Calendar records can use the shared editor in context;
- Atlas-owned records can expose Atlas edit/complete actions;
- other node-owned rows expose only explicitly safe owner actions or deep-link to the exact source;
- birthdays/holidays/rotating background layers are excluded from Agenda where defined by
  `30_Core_Daily_Coordination.md`.

## 9. People & birthdays

Atlas may manage important external contacts/birthdays for people who are not household login
Users/People.

Household member birthdays remain sourced from `Person.date_of_birth`. A linked Person must not get
a duplicate external contact merely for birthday display.

## 10. Permissions

Atlas follows central visibility/permission rules. Children may use permitted simple household
lists/checklists/Grocery, while private/restricted notes and adult-only material remain filtered.

UI hiding is not the security boundary.

## 11. Hub / Search / Notifications

Possible/current Atlas contributions include:

- my/household to-dos;
- Grocery/Shopping summaries;
- reminders/overdue items;
- quick capture;
- Agenda-related next actions.

Search uses permission-filtered owning data (D9).

Notifications include meaningful due/assignment/list events according to the shared notification
system. Web Push preferences/delivery are defined in `32_Core_Notifications_and_Push.md`, not in an
Atlas-specific notification implementation.

## 12. Events and integrations

Atlas publishes source-domain events for meaningful changes. Other domains can react through D4
without importing Atlas models.

Examples of permitted future interaction:

- Hearth produces missing ingredients → Atlas Grocery receives confirmed items;
- Inventory/Stock low item → suggest/add Grocery/Shopping item through a service/event contract;
- Home Assistant automation may consume an approved minimal Atlas event through the dedicated HA
  bridge.

Do not make Atlas depend on those future domains to function.

## 13. Attachments / safe links

Attachments use the shared protected attachment service.

Product URL preview/cache/watch uses the shared Link Import core boundary (`29_Core_Link_Import.md`)
rather than arbitrary Atlas scraping code.

## 14. Mobile / kiosk

Atlas is a high-frequency mobile surface:

- fast add/tick;
- large touch targets;
- simple Grocery use while shopping;
- Shopping product rows readable without horizontal tables;
- quick filters and obvious completion state.

Kiosk/child presentation stays simpler: permitted lists, checklists, Grocery and quick actions with
minimal typing; complex note/product management can remain web-only where appropriate.

## 15. Progressive detail

Basic use: create a list, add items, tick them off.

Standard use: assign People, dates, quantity/priority, reminders.

Detailed use: notes/attachments/product link import/price watch/advanced visibility where the
specific surface supports them.

The detailed mode must not make the basic shopping/checklist flow slower.

## 16. Data ownership

Exact schema is defined by current Django models/migrations. Atlas owns its note/list/list-item/
reminder/contact data and source dates. Calendar, Hub, Corners, Search and notifications are derived
or cross-cutting views of that data.

## 17. Risks and guardrails

Primary risk: Atlas becomes the dumping ground for every feature.

Guardrails:

- rewarded household work remains Meridian;
- durable reference remains Home Wiki;
- home planning remains Homestead;
- travel-specific plans remain Travel;
- meal/recipe semantics belong to Hearth;
- finance belongs to Solace;
- future Inventory owns stock-on-hand, not the Grocery list.

## 18. Completion state

Atlas's current everyday baseline is complete and in use: notes/lists, dedicated Grocery and
Shopping, due-date Calendar integration, Agenda/Appointments & events, People/birthdays, safe
product-link integration, mobile-friendly completion and permission-aware search/projections.

Future Atlas work should be driven by observed friction (templates/recurring lists/richer notes/
voice capture), not by expanding the node to absorb unrelated domains.