# Node Spec — Atlas

> Canonical. **V1 node.** Global rules from `00_README_and_Changelog.md` apply: base-model
> inheritance, calendar via the scheduling helper (`calendar_event_id`), one `recurrence_rule`
> (RRULE), `created_by/updated_by` = user / assignees = person, attachments via shared service,
> search via Postgres FTS, decoupling via the `events` signal interface.

## 1. Purpose

Atlas is HomeStack's general household-organisation node: a flexible home for everyday notes,
lists, checklists, simple reminders and quick capture. It absorbs lightweight organisational
features that don't justify their own node, keeping the rest of HomeStack uncluttered. It
serves adults, children (where permitted) and shared kiosk use.

## 2. Philosophy

Atlas answers: *"Where do we put the everyday things we need to remember, write down, check
off or organise?"* Simple by default, flexible when needed. It is **not** a project manager
(Projects), document vault (Documents/Attachments), recipe manager (Hearth) or finance tracker
(Solace).

## 3. What belongs in Atlas

Grocery/hardware/shopping lists; weekend to-do lists; camping or party checklists; quick
notes; household reminders; ad-hoc packing lists not tied to a Travel trip; morning/cleaning
checklists not tied to Meridian rewards; "things to buy / fix / ideas for later."

## 4. What does NOT belong in Atlas

Rewarded tasks/chores/points → **Meridian**. Bills/budgets/subscriptions → **Solace**.
Recipes/meal plans → **Hearth**. Tracked quantities/pantry stock → **Inventory**. Trip-specific
itinerary → **Travel**. Large multi-stage initiatives → **Projects**. Permanent reference
knowledge → **Home Wiki**.

## 5. Primary users

Admins, managers, users, permitted child accounts, kiosk users. Children may use simple lists
and checklists; complex note management is hidden/simplified for child accounts.

## 6. Key features

**Notes** — title, body, tags, category, visibility, attachments. V1 plain or simple rich
text; Markdown/templates parked.

**Lists** — types: general, to-do, grocery, shopping, checklist. Items carry text,
description, completed status, `assigned_to_person`, `due_at`, display order; `completed_by`
is a **user**, `created_by` is a **user**.

**Grocery/shopping mode** — add/tick items, quantity, optional category/notes, optional
assigned shopper (person), category sort, kiosk-friendly ticking, mobile shopping view. May
receive items from Hearth/Inventory later via signals.

**Checklists** — reusable lists for repeated routines (camping, school morning, leaving the
house, weekly reset, pet-sitter). Templates/reset/duplicate/recurring parked.

**Reminders** — simple reminders; dated reminders surface on Hub, Calendar and Notifications.

**Quick capture** — rapid add of note/list-item/reminder/to-do from Hub/mobile/kiosk; sorting
afterwards. (Foundational in V1, richer later.)

## 7. Permissions

Visibility: private · household · role_restricted · user_restricted. Default household.
Children see only permitted content. Enforced through the central resolver + visibility mixin.

## 8. Hub integration

Widgets: my to-dos · household list · shopping list · recent notes · reminders due · today's
checklist · quick add. Children get simplified widgets only.

## 9. Calendar integration

Dated Atlas items (reminder/to-do/checklist due dates) may appear on the Calendar via the
scheduling helper; the item owns its date and stores `calendar_event_id`. The user chooses
whether a dated item appears on the Calendar — not all do by default.

## 10. Notifications

Reminder due · assigned list item due · checklist due · (optional) shared/grocery list
updated. Future channels parked.

## 11. Events (signals)

Publishes: `atlas_note_created`, `atlas_list_created`, `atlas_list_item_added`,
`atlas_list_item_completed`, `atlas_reminder_due`, `shopping_list_updated`,
`checklist_completed`.
Consumes: `ingredient_missing`, `inventory_item_low`, `travel_packing_item_created`,
`project_task_created`.
Example: Hearth meal plan → Inventory pantry check → `ingredient_missing` → Atlas adds grocery
item.

## 12. Search

FTS over note title/body, list title, list-item text, tags, categories — permission-filtered.
Children never see restricted notes in results.

## 13. Attachments

Notes/lists/items may attach files via the shared service (photo on a shopping item, PDF on a
note). Atlas never implements its own storage.

## 14. Kiosk

Large list cards, simple checklists, shopping-list ticking, quick reminders, minimal typing,
clear visual states, touch-first. No complex note editing by default; children see only
permitted lists/checklists.

## 15. Mobile

Quick-add button, large tap targets, easy item completion, simple filtering, fast grocery use
while shopping. Offline parked.

## 16. Progressive detail

Basic: create list, add items, tick off. Standard: due dates, assign people, notes,
categories. Detailed: tags, attachments, templates, recurring checklists, advanced visibility.

## 17. Data model

`atlas_notes`, `atlas_lists` (`list_type` ∈ todo/grocery/checklist/shopping/general),
`atlas_list_items` (`assigned_to_person_id`, `completed_by_id` user, `recurrence_rule` if
recurring, `calendar_event_id`), `atlas_reminders` (`recurrence_rule`, `calendar_event_id`).
All inherit `HouseholdBaseModel`. Shared: attachments, tags, categories, calendar_events,
notifications, audit_logs.

## 18. V1 scope

Notes · lists · list items · grocery/shopping mode · checklists · simple reminders · Hub
widget · calendar integration for dated items · FTS · basic permissions · kiosk checklist view
· mobile-friendly lists.

## 19. Risks & mitigation

Risk: Atlas sprawling, or overlapping Projects/Home Wiki/Meridian. Mitigation: keep it to
lightweight organisation; push reference content to Home Wiki, rewarded tasks to Meridian,
large initiatives to Projects; keep kiosk simple; use progressive detail.

## 20. Completion criteria

Users create notes and lists, add/complete items, build grocery lists and simple reminders;
dated items appear on Calendar; content appears on Hub; permitted content is searchable;
permissions enforced; kiosk and mobile views usable; follows the shared design system.
