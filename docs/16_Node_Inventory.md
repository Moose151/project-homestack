# Capability Spec — Stock & Storage (former Inventory plan)

> **Status:** future proposal, not implemented. The preferred direction is an optional
> **Homestead → Stock & storage** capability rather than a separate top-level Inventory node.
> This document preserves the possible domain contract without implying that its models/routes/
> widgets already exist.

## 1. Purpose

Stock & storage would help the household answer:

- What consumables/items do we have?
- Where are they stored?
- What is low or expiring?
- What should be added to the household Grocery/Shopping list?

It should remain optional. HomeStack must continue to work well for households that do not want to
maintain stock quantities.

## 2. Ownership boundaries

**Potential Stock & storage ownership:**

- pantry/fridge/freezer stock;
- cleaning supplies/toiletries/household consumables;
- pet food and other ordinary stored consumables;
- storage locations/boxes;
- quantity/unit/low-stock threshold;
- expiry/best-before information;
- stock adjustment/history only to the depth useful in real household use.

**Belongs elsewhere:**

- the actual household shopping list → Atlas Grocery/Shopping;
- recipes/meal plans → Hearth;
- pet care/profile/treatments → Pets;
- home appliances/warranties → Homestead;
- vehicles/tools/valuables → future Assets & vehicles capability;
- medication/medical stock → Health;
- finance/budget/payment history → Solace.

## 3. Homestead capability position

If built, Stock & storage should appear as an optional Homestead capability because rooms/storage
locations provide a natural physical context and this avoids another top-level navigation item.

That presentation decision must not make Homestead UI code the reusable business boundary. Other
services such as Hearth, Pets or Atlas should interact through approved selectors/services/events.

Do not create a standalone `inventory` node first and promise to consolidate it later unless a new
explicit product decision changes this direction.

## 4. Candidate data model

Only create these models when implementation is approved. A small first slice could include:

### StorageLocation

- name;
- optional Room/area relationship;
- type/category;
- notes;
- visibility if needed.

### StockItem

- name;
- location;
- quantity/unit;
- low-stock threshold;
- optional expiry date;
- category;
- notes;
- optional attachment/image;
- household/base-model fields.

Avoid a complex warehouse/transaction system unless actual use demands it.

## 5. Actions

Possible useful actions:

- add/update quantity;
- mark low/empty;
- move location;
- consume/restock;
- add/suggest item to Atlas Grocery/Shopping;
- view expiring items.

Fast manual correction is more important than pretending every household stock movement can be
perfectly automated.

## 6. Atlas Grocery/Shopping integration

Atlas is the shopping-list source of truth.

Stock & storage may propose/add a required item through an approved service/event contract, but it
does not create another shopping-list database.

Examples:

- low milk → propose/add milk to Atlas Grocery;
- cleaning supply empty → propose/add replacement to Atlas Shopping/Grocery according to the
  household workflow;
- ticking an Atlas item bought may optionally update stock if the user confirms the handoff.

Keep these interactions idempotent enough to avoid duplicate shopping spam.

## 7. Hearth integration

Hearth does **not** depend on Stock & storage existing.

Hearth can always send reviewed recipe ingredients to Atlas Grocery. If Stock & storage is later
enabled, Hearth may query it to estimate what is already on hand before proposing missing
ingredients.

Stale/unknown stock must be presented honestly rather than silently suppressing a grocery item.

## 8. Pets integration

Pets may use Stock & storage for pet-food quantity/low-stock context in the future. Pet profile,
feeding/care schedule and treatments remain Pets-owned.

## 9. Dates / Calendar / notifications

Only meaningful dated facts should project into Calendar, such as an expiry/replacement reminder
where that is useful. Do not create recurring Calendar noise simply because an item exists.

Low-stock/expiry notifications use the shared Notifications/Web Push system and user preferences.

## 10. Hub and Search

Potential useful Hub summaries:

- low stock;
- expiring soon;
- items needing shopping action.

Search would cover permitted item/location/category/notes data using the normal permission-aware
search pattern.

Neither Hub nor Search owns stock state.

## 11. Permissions / kiosk

Most household consumables can be household-visible, while restricted storage locations/items can
use the standard permission/visibility model.

Medical items belong in Health rather than relying on Inventory visibility settings.

A future kiosk surface could support simple view/use/add-to-Grocery actions, but kiosk support is
not a prerequisite for the capability.

## 12. Future enhancements

Only after a useful basic capability exists:

- barcode/QR scanning;
- storage labels;
- bulk import;
- pantry-aware Hearth suggestions;
- expiry dashboard;
- purchase/consumption trends.

## 13. Implementation gate

Do not implement until real household use shows that maintaining stock-on-hand will provide enough
value to justify the data-entry burden.

If approved, the first completion point is: the household can define storage locations, track a
small set of useful consumables, see low/expiry attention and send required items into existing
Atlas Grocery/Shopping without creating another top-level Inventory node.