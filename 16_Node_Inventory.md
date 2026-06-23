# Node Spec — Inventory

> Canonical. **Later node** (post-V1). Global rules from `00_README_and_Changelog.md` apply.

## 1. Purpose & philosophy

Tracks household consumables and stored items so the household knows what's on hand, what's
low, what's expiring and what to add to shopping. Answers: *"What do we have, where is it, and
do we need more?"* Not an asset manager — valuable/serviced/warrantied items → Assets.

## 2. Belongs / does not belong

**Belongs:** pantry/fridge/freezer items, cleaning supplies, toiletries, pet food, consumables,
storage-box contents, low-stock alerts, expiry reminders, location tracking.
**Not:** vehicles/appliances/tools → Assets; recipes → Hearth; shopping lists → Atlas;
warranties/documents → Assets/Documents; large projects → Projects.

## 3. Key features

**Locations** — pantry, fridge, freezer, bathroom, laundry, garage, shed, storage, other.
**Items** — name, location, quantity, unit, `low_stock_threshold`, `expiry_date`, category,
notes, photo/attachment; `updated_by` = user.
**Actions** — add, use, mark low, mark empty, move, update quantity, add to shopping list.

## 4. Permissions

Usually household-visible; some locations/items may be restricted. (Medication storage belongs
in Health, not Inventory.)

## 5. Hub / Calendar / Notifications

Widgets: low stock · expiring soon · recently added · shopping suggestions · pet-food status.
Calendar (via helper): expiry reminders, recurring restock, consumable-replacement reminders
(unless better handled by Assets), `recurrence_rule`. Notifications: low stock · expired ·
expiring soon · recurring restock due.

## 6. Events (signals)

Publishes: `inventory_item_low`, `inventory_item_expiring`, `inventory_item_used`,
`inventory_item_added`, `inventory_shopping_required`.
Consumes: `meal_plan_created`, `ingredient_required`, `shopping_item_completed`,
`pet_food_low`.
Example: Hearth meal plan → Inventory checks ingredients → missing items sent to Atlas grocery
list.

## 7. Search / Kiosk

FTS over item names, locations, categories, notes. Kiosk: view low-stock, add to shopping list,
mark used, view pantry/freezer — large buttons, minimal typing.

## 8. Data model

`inventory_locations`, `inventory_items` (`low_stock_threshold`, `expiry_date`,
`calendar_event_id` where dated, `recurrence_rule` where recurring). Inherit
`HouseholdBaseModel`.

## 9. Scope & completion

Initial: locations · items · quantity · low-stock thresholds · expiry dates · Hub low-stock
widget · Atlas shopping-integration foundation · FTS · basic permissions · mobile list view.
Complete when users track consumables, see low-stock/expiry reminders, and send items to Atlas
shopping lists. Future: barcode/QR, expiry dashboard, smart suggestions, bulk import, Hearth
pantry checks.
