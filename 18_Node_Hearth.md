# Node Spec — Hearth

> Canonical. **Later node** (post-V1; benefits from Inventory existing). Global rules from
> `00_README_and_Changelog.md` apply.

## 1. Purpose & philosophy

Manages meals, recipes and meal planning, and helps generate grocery needs. Answers: *"What are
we eating, what do we need, and what meals do we like?"* Does not own general groceries (Atlas)
or pantry stock (Inventory) — it uses them.

## 2. Belongs / does not belong

**Belongs:** recipes, meal plans, weekly schedule, ingredients, favourite meals, preferences,
meal categories, grocery generation; leftovers/batch cooking (future).
**Not:** pantry quantity → Inventory; grocery list → Atlas; food budget → Solace;
health-specific diet records → Health; general notes → Atlas.

## 3. Key features

**Recipes** — title, description, ingredients, instructions, prep/cook time, servings, category,
tags, favourite status, photo.
**Meal plans** — `planned_for` date, meal type (breakfast/lunch/dinner/snack/other), recipe,
notes, `assigned_to_person` (cook, optional), `calendar_event_id`.
**Grocery generation** — collect ingredients → (future) check Inventory → send missing items to
Atlas via signals.

## 4. Permissions

Mostly household-visible; some notes manager/admin only. Children see simple meal cards, not
complex recipe management by default.

## 5. Hub / Calendar / Notifications

Widgets: dinner tonight · weekly meal plan · favourite meals · meal suggestions · grocery needs
(via Atlas). Calendar (via helper): planned meals, visually distinct and simple. Notifications:
meal planned · prep reminder · shopping needed · leftovers expiring (future).

## 6. Events (signals)

Publishes: `recipe_created`, `meal_plan_created`, `meal_plan_updated`, `ingredients_required`,
`shopping_required`.
Consumes: `inventory_item_low`, `person_preference_updated`, `shopping_list_completed`.
Example: meal plan created → `ingredients_required` → Inventory checks stock → Atlas receives
missing items.

## 7. Search / Kiosk

FTS over recipe title, ingredients, instructions, tags, meal notes. Kiosk: dinner tonight,
weekly meals, recipe image cards, a simple "what's for dinner?" screen, future meal voting —
understandable at a glance by children.

## 8. Data model

`hearth_recipes`, `hearth_recipe_ingredients`, `hearth_meal_plans` (`assigned_to_person_id`,
`calendar_event_id`). Inherit `HouseholdBaseModel`.

## 9. Scope & completion

Initial: recipes · meal plans · dinner-tonight widget · calendar integration · recipe search ·
basic permissions · kiosk meal view. Complete when users create recipes, plan meals, view meals
on Calendar and Hub, and use kiosk dinner/meal-plan views. Future: recipe import, meal voting,
nutrition, leftovers, batch cooking, preference profiles, Inventory checking, automatic grocery
generation.
