# Node Spec — Atlas

> **Status:** shipped and in daily use. Atlas is HomeStack's quick, low-friction household
> capture surface — Grocery, lightweight To-dos and Lists & Notes (D19, v0.40). Global rules
> D1–D24 apply.

## 1. Purpose

Atlas is the place somebody remembers something, types it, and moves on.

It answers: **What do we need to buy, do or write down right now?**

Atlas must remain lightweight. It is not a full task-management system, the finance system,
reward economy, recipe database, property system or large-project manager. **Meridian** remains
the structured household chores/tasks system — recurring chores, assignment/accountability,
rewards and richer task workflow. Atlas is deliberately the opposite of that: minimal metadata,
no workflow, no dependencies.

## 2. Three primary areas (D19 §B)

Atlas is simplified to exactly three primary areas:

1. **Grocery** — the one household shopping list.
2. **To-dos** — the Household list, plus one personal list per active household member.
3. **Lists & Notes** — arbitrary checklists and freeform notes.

Everything else Atlas surfaces (Agenda, Appointments & events, People & birthdays) is a
secondary, Calendar-adjacent convenience, not a fourth primary area.

## 3. What belongs elsewhere

- rewarded chores/tasks/points → Meridian;
- bills/budgets/financial purchases → Solace;
- recipes/meal plans → Hearth;
- property/room plans/products → Homestead;
- trip itinerary/packing tied to a Trip → Travel;
- durable household reference/procedures → Home Wiki;
- medical information → Health;
- complex cross-domain project planning → only a future Projects domain if real use justifies it.

## 4. Grocery — one list only (D19 §C)

There is exactly **one** Grocery list per household — not one per person, and no per-item
owner/shopper. Every household member can view, add, edit, check off and restore items on it.

An item requires only a name. Optional properties: quantity, a short note, a simple category.
Category grouping is a lightweight client-side heuristic (keyword-matched from the title), not a
stored field — it costs nothing to change and never conflicts with anyone else's data, and can be
switched off in favour of a flat list.

Checked-off items move into a collapsed "Bought" section rather than disappearing immediately;
"Clear bought" removes them permanently. Duplicate-title detection avoids a second "Milk" row.
Frequently-bought titles (from completed items) are offered as one-tap suggestions.

Grocery does **not** have: assigned shopper, store assignment, budgeting, prices, complex
statuses or approval workflow. Money/Meals integrations may read from or write into this one list
in future without making Grocery itself more complicated (see §12).

## 5. To-dos (D19 §D/§E/§F/§G)

To-dos replace the old standalone "Reminder" object. There is no longer a separate choice between
"To-do, Reminder, Task or Calendar Event" inside Atlas — a reminder is a notification schedule
attached to a To-do, not a competing object type.

Lists: the shared **Household** list, plus exactly one **personal** list per active Person. Every
household member can view and edit both the Household list and every other member's personal
list — the list itself is the ownership/context, so there is no per-item "Assigned to" field. An
item can be moved between lists ("Move to → Household / Nick / …").

A To-do requires only a title. Optional: due date/time, a simple ★ Important flag (deliberately
not High/Medium/Low priority), a note, and notification offsets.

**Notification offsets**: a dated To-do can select multiple offsets from a curated menu — at
time, 15/30 minutes before, 1/2 hours before, 1/2 days before, 1 week before. Selections are
idempotent, reschedule automatically when the due date/time changes, and stop firing the moment
the To-do is completed or deleted (nothing is pre-scheduled; each scheduler run recomputes from
the item's current `due_at`/`notify_offsets`). This reuses the existing shared notification
infrastructure (`apps.notifications`) — see §11.

**Today view**: a lightweight aggregation of overdue and due-today To-dos across the Household
list and every personal list. It is not a project planner; the Dashboard's "Upcoming" widget
remains the broader cross-HomeStack view.

Completed To-dos leave the active list, remain visible in a collapsed "Completed" section, and
are restorable.

### Legacy: AtlasReminder

The pre-D19 `AtlasReminder` model still exists and still backs Calendar's own "quick-create a
reminder" flow (a different surface from Atlas's own UI) — it is not exposed anywhere in Atlas's
UI any more, and nothing new is created through Atlas itself as a `AtlasReminder`. Existing
reminders were copied into the appropriate To-do list at migration time; the original rows are
kept (not deleted) since Calendar's quick-create still depends on them.

## 6. Lists & Notes (D19 §H)

Everything miscellaneous: `New → Checklist` or `New → Note`.

A **checklist** (Bunnings run, holiday packing, camping gear, Christmas presents, movies to
watch, things to repair) supports a title, quick-add items, check/uncheck, and a completed
section — the same lightweight shape as a To-do list, without the Household/personal ownership
model or notification offsets.

A **note** is lightweight free-form text (title + body + household/private visibility).

Personal (owned) checklists can still belong to a Person and surface in Corners; other members
suggest changes through the existing bounded suggestion flow rather than editing someone else's
personal list directly — this personal-list/suggestion behaviour is unchanged from before D19 and
does **not** apply to To-do lists (§5), which every member can edit directly.

## 7. Agenda / Appointments & events / People & birthdays

Secondary, Calendar-adjacent tabs — not part of the three primary areas, kept because they are
useful without duplicating Calendar's own UI.

**Agenda** is an actionable permission-filtered projection of Calendar/source-owned work. It does
not create duplicate Atlas records for Calendar-owned appointments or other nodes' records.

**Appointments & events** is the browse/manage projection for standalone Calendar records with
type/person/date filtering.

**People & birthdays** manages external contacts (people without a HomeStack login) and their
birthdays. Household member birthdays are sourced from `Person.date_of_birth`; **pet** birthdays
are sourced from `Pet.date_of_birth` and appear automatically on Calendar via the same virtual,
computed-on-read mechanism as People — see `13_Node_Pets.md` and `30_Core_Daily_Coordination.md`.
Neither is a separate Atlas record a user has to remember to create annually, and neither is ever
worded as "due" or "overdue".

Rules:

- standalone Calendar records can use the shared editor in context;
- Atlas-owned records can expose Atlas edit/complete actions;
- other node-owned rows expose only explicitly safe owner actions or deep-link to the exact
  source;
- birthdays/holidays/rotating background layers are excluded from Agenda where defined by
  `30_Core_Daily_Coordination.md`.

## 8. Permissions (D19 §U)

- **Grocery**: every household member can view/edit the one list.
- **To-dos**: every household member can view/edit the Household list and every person's list.
- **Lists & Notes**: unchanged pre-D19 personal-list/suggestion behaviour.

Children may use permitted simple checklists/Grocery/To-dos, while private/restricted notes and
adult-only material remain filtered. UI hiding is not the security boundary — one household must
never access another household's data.

## 9. Hub / Search / Notifications

Dashboard widgets: a dedicated **Grocery** widget (remaining count, a few current items, quick
add, "View grocery list") and a **To-do** widget (overdue/today, quick add into Household or the
current user's personal list, "View To-dos"). Grocery items are never rendered under To-dos —
this was a real bug (a grocery item leaking into the to-do widget because both derived from the
same underlying list-item table) and is now fixed at the query layer:
`apps.atlas.selectors.list_open_items` filters strictly to `list_type='todo'`, and Grocery has
its own selector/widget entirely.

Search finds To-dos, Notes, Checklists and Grocery items. Within Atlas, simple views (Active /
Completed / Today) are sufficient — no complex filtering UI.

Notification offsets are described in §5. The scheduling mechanism (`apps/notifications/tasks.py`
`run_due_todo_offsets`) is additive alongside the existing 24h/morning-of/due-at leads used by
standalone Calendar entries and legacy `AtlasReminder`s — not a second independent scheduler.

## 10. Mobile / kiosk

Atlas is a high-frequency mobile surface, especially while shopping or walking around the house:

- persistent quick-add on every list, large tap targets, minimal modals;
- one-tap check/uncheck;
- no horizontal scrolling, no dense desktop-style forms on mobile;
- routine creation never opens a large modal — only the title is required, everything else is
  editable after creation.

Kiosk/child presentation stays simpler: permitted lists, checklists, Grocery and To-dos with
minimal typing; notes remain web-only where appropriate.

## 11. Data ownership

Exact schema is defined by current Django models/migrations. Atlas owns its note/list/list-item/
reminder/contact data and source dates. Calendar, Hub, Corners, Search and notifications are
derived or cross-cutting views of that data.

## 12. Risks and guardrails

Primary risk: Atlas becomes the dumping ground for every feature, or quietly regrows into a
second task-management system.

Guardrails:

- rewarded household work remains Meridian — do not move Meridian features into Atlas;
- durable reference remains Home Wiki;
- home planning remains Homestead;
- travel-specific plans remain Travel;
- meal/recipe semantics belong to Hearth — a future Hearth meal plan may populate missing
  ingredients into this existing Grocery list, but Grocery itself gains no budgeting, store
  assignment or pricing to support that;
- finance belongs to Solace;
- future Inventory owns stock-on-hand, not the Grocery list;
- no High/Medium/Low priority, Kanban boards, subtasks, dependencies or approval workflow on
  To-dos — a simple ★ Important flag is sufficient.

## 13. Completion state

Atlas's D19 baseline is complete and in use: single-list Grocery, Household + personal To-do
lists with configurable notification offsets and a Today view, merged Lists & Notes (checklists +
notes), Agenda/Appointments & events, People & Pet birthdays, mobile-friendly completion and
permission-aware search/projections.

Future Atlas work should be driven by observed friction, not by expanding the node to absorb
unrelated domains.
