# Node Spec — Hearth

> **Status:** important future everyday-life node. Hearth no longer depends on Inventory being
> implemented first: the existing Atlas Grocery list is the household shopping source of truth,
> and Hearth should send generated ingredient needs there. A future Stock & storage capability can
> optionally improve pantry awareness without becoming a prerequisite.

## 1. Purpose

Hearth manages recipes and meal planning and helps turn meal choices into practical household
shopping needs.

It answers:

- What are we eating?
- What recipes do we use?
- What needs preparing?
- Which ingredients need to go onto the household Grocery list?

Hearth should feel useful even if the household never tracks pantry stock in detail.

## 2. Ownership boundaries

**Hearth owns:**

- recipes;
- recipe ingredients/instructions;
- meal plans and planned meals;
- meal-specific preferences/favourites where implemented;
- ingredient requirement calculations.

**Hearth does not own:**

- the household Grocery list → Atlas;
- general Shopping/product purchases → Atlas Shopping;
- pantry/stock-on-hand → future Inventory/Stock & storage capability;
- food budget/payment history → Solace;
- medical/dietary health records → Health;
- general household notes → Atlas.

The key rule is that meal planning may **contribute items to Atlas Grocery** but does not maintain a
second competing grocery database.

## 3. Recipes

A recipe may include the implemented/future combination of:

- title and description;
- ingredients with amount/unit/text;
- instructions/steps;
- prep/cook/total time;
- servings;
- category/tags;
- favourite state;
- photo/attachment;
- source/provenance for safely imported recipes.

Recipe data should remain editable after import. Imported text must be confirmed/normalized rather
than treated as an immutable external copy.

## 4. Meal planning

Meal-plan records own their planned date/time/meal type and optional assigned cook/person.

Planned meals may project into Calendar through the shared scheduling helper (D7). Calendar is a
projection; Hearth remains the source of truth for the meal plan.

Useful first surfaces:

- **Dinner tonight**;
- weekly meal plan;
- upcoming meals;
- recipe selection/favourites;
- simple "what are we eating?" household/kiosk view.

## 5. Grocery generation

This is the most important cross-domain contract.

A meal plan can calculate ingredient requirements for selected recipes/servings. The user can
review the result and send missing/required ingredients into the existing **Atlas Grocery** list.

Requirements:

- do not create a separate Hearth grocery list/table;
- combine obviously identical ingredients where practical but keep user review/editability;
- preserve useful quantity/unit information without forcing perfect normalization;
- avoid silently deleting or rewriting existing Atlas Grocery items;
- generated items should carry enough provenance/source context to explain why they were added if
  the shared list model supports it;
- repeated generation must avoid obvious duplicate spam where the same meal/ingredients are sent
  twice.

### Optional future Stock & storage integration

If the household later enables Inventory/Stock & storage, Hearth may ask that capability which
ingredients appear to be on hand and only propose missing quantities. This is an enhancement, not a
Hearth dependency.

If stock data is stale/unknown, the UI should say so and let the user decide rather than pretending
the pantry state is exact.

## 6. Recipe import

Future recipe import should reuse the existing safe link-import principles where possible.

Preferred sources are structured recipe metadata (for example Schema.org Recipe) and user-confirmed
fields. The importer must:

- obey SSRF/URL safety boundaries;
- never forward HomeStack cookies/credentials;
- avoid bypassing bot protection/paywalls;
- present extracted fields for review;
- preserve provenance;
- fail honestly to manual entry when a page withholds usable data.

Do not build a general web scraper merely for Hearth.

## 7. Permissions

Most ordinary recipes/meal plans will be household-visible, but the existing visibility/permission
model remains available.

Children may see simple meal cards/recipes where permitted. Administrative/richer recipe editing can
remain adult-focused if that produces a clearer child/kiosk experience.

Medical/allergy/diet information that is genuinely health-sensitive belongs in Health rather than
being exposed broadly through Hearth notes.

## 8. Hub / Calendar / Notifications

Potential Hearth contributions:

- Dinner tonight;
- next meals/week plan;
- prep reminder;
- grocery ingredients still needed;
- leftovers reminders where later implemented.

Calendar projections use the shared scheduling helper.

Notification delivery uses the shared notification/preferences/Web Push system rather than a
Hearth-specific channel implementation.

## 9. Events and integrations

Hearth publishes meaningful domain changes through D4, for example meal-plan/ingredient requirement
updates.

Likely relationships:

- Hearth → Atlas Grocery: reviewed ingredient additions;
- future Stock & storage → Hearth: optional on-hand information;
- Solace: optional future budget context only, without Hearth owning finance;
- Home Assistant: future approved meal-related events/household displays through the dedicated
  bridge if useful.

No node-model imports should be introduced for these interactions.

## 10. Search / attachments

Recipe title, ingredients, instructions/tags and meal notes may participate in permission-aware
search.

Images/documents use the shared attachment system rather than Hearth-specific storage.

## 11. Mobile and kiosk

Hearth should be highly usable on a phone in the kitchen/shop context:

- quick recipe lookup;
- readable ingredient/step layout;
- easy serving adjustment;
- fast meal-plan changes;
- one clear handoff to Atlas Grocery.

Kiosk should emphasize the household-facing view: today's meal, upcoming meals and simple recipe
cards rather than dense recipe administration.

## 12. Initial delivery slice

A useful first Hearth release should include:

1. recipes;
2. meal planning;
3. Dinner tonight / upcoming meal Hub presentation;
4. Calendar integration where useful;
5. recipe search;
6. basic permissions;
7. responsive household/kiosk presentation;
8. reviewed generation of ingredients into **Atlas Grocery**.

Do not block this release on Inventory/Stock & storage, nutrition analysis, AI or external APIs.

## 13. Future enhancements

Possible later additions:

- structured recipe URL import;
- meal voting/suggestions;
- leftovers/batch cooking;
- nutrition information;
- pantry-aware ingredient subtraction;
- household preference profiles;
- seasonal/favourite rotation;
- richer cooking timers/instructions.

These should be prioritized by actual household use rather than built as prerequisites.

## 14. Completion criteria

Hearth's first meaningful completion point is reached when the household can save recipes, plan a
week of meals, immediately see what is for dinner, have planned meals appear appropriately in
HomeStack, and send reviewed ingredients into the existing Atlas Grocery list without duplicate
sources of truth.