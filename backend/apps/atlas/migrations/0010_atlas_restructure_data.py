"""Data migration for the simplified Atlas product model (v0.40, D19).

Atlas becomes Grocery + To-dos + Lists & Notes. This migration adapts existing data instead
of discarding it:

1. Legacy ``shopping``/``wishlist`` lists fold into ``checklist`` (Lists & Notes) — their
   items are preserved as-is, they simply stop being a separate top-level concept.
2. Exactly one household Grocery list is kept; any extra grocery lists have their items moved
   into the oldest one, then are soft-deleted (soft-delete only — nothing is hard-deleted).
3. Exactly one shared Household To-do list, plus exactly one personal To-do list per active
   Person, are ensured the same way (create if missing, merge duplicates into the oldest).
4. Grocery becomes assignee-free (D19 §C): any pre-existing per-item assignee on a grocery
   item is cleared. The underlying ``assigned_to_people`` relation itself is not removed —
   only reviewed schema migrations should ever drop a relation, and it is still meaningful
   for To-do items.
5. Existing ``AtlasReminder`` rows are copied into To-do items in the appropriate list (the
   sole assignee's personal list if there is exactly one, else the Household list), carrying
   over title/body/due date/assignees, and translated into the new ``notify_offsets`` shape
   (at-time + 1-day-before, matching the reminder's old 24h/due-at behaviour when it had
   notifications enabled). The original ``AtlasReminder`` rows are NOT deleted — Calendar's
   quick-create "Reminder" flow still reads/writes them (docs/40_Atlas_Product_Model.md), and
   nothing here would be safely reversible if they were removed.
"""
from __future__ import annotations

from django.db import migrations
from django.utils import timezone


def restructure_forward(apps, schema_editor):
    AtlasList = apps.get_model("atlas", "AtlasList")
    AtlasListItem = apps.get_model("atlas", "AtlasListItem")
    AtlasReminder = apps.get_model("atlas", "AtlasReminder")
    Person = apps.get_model("people", "Person")
    Household = apps.get_model("core", "Household")

    now = timezone.now()

    def merge_into_oldest(queryset):
        rows = list(queryset.order_by("created_at", "id"))
        if not rows:
            return None
        canonical = rows[0]
        for extra in rows[1:]:
            AtlasListItem.objects.filter(atlas_list=extra).update(atlas_list=canonical, updated_at=now)
            extra.deleted_at = now
            extra.updated_at = now
            extra.save(update_fields=["deleted_at", "updated_at"])
        return canonical

    for household in Household.objects.all():
        AtlasList.objects.filter(
            household=household, list_type__in=["shopping", "wishlist"], deleted_at__isnull=True,
        ).update(list_type="checklist", updated_at=now)

        canonical_grocery = merge_into_oldest(
            AtlasList.objects.filter(
                household=household, list_type="grocery", owner_person__isnull=True,
                deleted_at__isnull=True,
            )
        )
        if canonical_grocery is None:
            canonical_grocery = AtlasList.objects.create(
                household=household, title="Grocery", list_type="grocery",
                created_at=now, updated_at=now,
            )

        canonical_household_todo = merge_into_oldest(
            AtlasList.objects.filter(
                household=household, list_type="todo", owner_person__isnull=True,
                deleted_at__isnull=True,
            )
        )
        if canonical_household_todo is None:
            canonical_household_todo = AtlasList.objects.create(
                household=household, title="Household", list_type="todo",
                created_at=now, updated_at=now,
            )

        person_todo_by_person: dict[int, object] = {}
        for person in Person.objects.filter(household=household, deleted_at__isnull=True):
            canonical_personal = merge_into_oldest(
                AtlasList.objects.filter(
                    household=household, list_type="todo", owner_person=person,
                    deleted_at__isnull=True,
                )
            )
            if canonical_personal is None:
                canonical_personal = AtlasList.objects.create(
                    household=household, title=person.display_name, list_type="todo",
                    owner_person=person, created_at=now, updated_at=now,
                )
            person_todo_by_person[person.id] = canonical_personal

        for item in AtlasListItem.objects.filter(atlas_list=canonical_grocery):
            item.assigned_to_people.clear()

        for reminder in AtlasReminder.objects.filter(household=household, deleted_at__isnull=True):
            assignee_ids = list(reminder.assigned_to_people.values_list("id", flat=True))
            target_list = canonical_household_todo
            if len(assignee_ids) == 1 and assignee_ids[0] in person_todo_by_person:
                target_list = person_todo_by_person[assignee_ids[0]]

            notify_offsets = [0, 1440] if (reminder.notifications_enabled and reminder.due_at) else []

            item = AtlasListItem.objects.create(
                household=household, atlas_list=target_list, title=reminder.title,
                notes=reminder.body, due_at=reminder.due_at, is_all_day=reminder.is_all_day,
                notify_offsets=notify_offsets, position=0,
                created_at=reminder.created_at, updated_at=now,
            )
            if assignee_ids:
                item.assigned_to_people.set(assignee_ids)


def restructure_reverse(apps, schema_editor):
    # Merges/soft-deletes/reminder-to-todo copies are not safely undoable — no data is lost
    # (everything is preserved as soft-deleted rows or additional to-do items), but reversing
    # would require guessing which lists/items were pre-existing vs. migration-created.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("atlas", "0009_todo_and_grocery_fields"),
        ("people", "0001_initial"),
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(restructure_forward, restructure_reverse),
    ]
