"""Data migration for the simplified Atlas product model (v0.40, D19).

Atlas becomes Grocery + To-dos + Lists & Notes. This migration adapts existing data instead
of discarding it. Nothing is hard-deleted anywhere below: lists and reminders that stop being
part of the product are soft-deleted, which keeps the rows readable for support/rollback while
taking them out of every ordinary query.

1. Legacy ``shopping``/``wishlist`` lists fold into ``checklist`` (Lists & Notes) — their
   items are preserved as-is, they simply stop being a separate top-level concept.
2. Exactly one Grocery list survives per household. **Every** grocery list is folded in,
   including per-person ones: a household that had "Mum's grocery" and "Dad's grocery" ends up
   with one shared list holding both sets of items. Selecting only ``owner_person__isnull=True``
   here would have left personal grocery lists active and their items stranded outside the one
   list the product now shows.
3. Exactly one shared Household To-do list, plus exactly one personal To-do list per active
   Person, are ensured the same way (create if missing, merge duplicates into the oldest).
   Personal To-do lists belonging to people who have since been deleted are retired too, with
   their items moved to the Household list — otherwise the items live on a list the To-dos tab
   would still render under a deleted person's name.
4. Grocery becomes assignee-free (D19 §C): per-item assignees are cleared *after* the merge, so
   items that arrived from a personal grocery list are cleared as well. The underlying
   ``assigned_to_people`` relation itself is not removed — only reviewed schema migrations
   should ever drop a relation, and it is still meaningful for To-do items.
5. Existing ``AtlasReminder`` rows become To-do items and the reminder itself is retired.

   The retirement is the point. A migrated reminder that stayed active would be notified
   twice for the same thing — once by ``run_due_reminders`` (which sweeps the reminder's
   CalendarEvent) and again by ``run_due_todo_offsets`` (which reads the new To-do's
   ``notify_offsets``) — and would appear twice on the Calendar and in Upcoming. So each
   reminder's existing CalendarEvent is *repointed* at its new To-do rather than left behind or
   deleted: the household keeps exactly one calendar entry, now owned by the To-do, and the
   AtlasReminder row is soft-deleted with its ``calendar_event_id`` cleared. The row survives
   as archival data; it simply no longer participates in any calendar or notification workflow.
"""
from __future__ import annotations

from django.db import migrations
from django.utils import timezone


def _notify_offsets_for(reminder) -> list[int]:
    """The old fixed reminder leads, expressed as the new per-item offsets.

    A reminder with notifications on used to get a 24-hour lead, a morning-of digest entry and
    (when it had a real time) a notification at the due moment. The closest honest translation
    is "1 day before" plus "at time".

    All-day reminders deliberately get only the day-before lead: their ``due_at`` is midnight,
    so carrying "at time" across would manufacture a midnight notification the household never
    asked for — the old morning-of digest is what actually served them, and there is no
    morning-of offset in the curated menu.
    """
    if not (reminder.notifications_enabled and reminder.due_at):
        return []
    return [1440] if reminder.is_all_day else [0, 1440]


def _notes_for(reminder) -> str:
    """The reminder body, plus its recurrence rule if it had one.

    A To-do has no recurrence field. Recurrence was display-only on reminders anyway (D8 defers
    RRULE expansion, and the notification sweep only ever read ``start_at``), but dropping the
    string silently would lose the household's stated intent, so it is carried into the notes.
    """
    notes = reminder.body or ""
    if reminder.recurrence_rule:
        suffix = f"Repeats: {reminder.recurrence_rule}"
        notes = f"{notes}\n\n{suffix}".strip() if notes else suffix
    return notes


def restructure_forward(apps, schema_editor):
    AtlasList = apps.get_model("atlas", "AtlasList")
    AtlasListItem = apps.get_model("atlas", "AtlasListItem")
    AtlasReminder = apps.get_model("atlas", "AtlasReminder")
    CalendarEvent = apps.get_model("scheduling", "CalendarEvent")
    Person = apps.get_model("people", "Person")
    Household = apps.get_model("core", "Household")

    now = timezone.now()

    def retire_into(canonical, extras):
        """Move every item off ``extras`` onto ``canonical``, then soft-delete ``extras``."""
        for extra in extras:
            if extra.id == canonical.id:
                continue
            AtlasListItem.objects.filter(atlas_list=extra).update(atlas_list=canonical, updated_at=now)
            extra.deleted_at = now
            extra.updated_at = now
            extra.save(update_fields=["deleted_at", "updated_at"])

    def merge_into_oldest(queryset):
        rows = list(queryset.order_by("created_at", "id"))
        if not rows:
            return None
        canonical = rows[0]
        retire_into(canonical, rows[1:])
        return canonical

    for household in Household.objects.all():
        AtlasList.objects.filter(
            household=household, list_type__in=["shopping", "wishlist"], deleted_at__isnull=True,
        ).update(list_type="checklist", updated_at=now)

        # --- Grocery: one list, whoever used to own it -------------------------------------
        grocery_rows = list(
            AtlasList.objects.filter(
                household=household, list_type="grocery", deleted_at__isnull=True,
            ).order_by("created_at", "id")
        )
        # Prefer an already-shared list as the survivor; fall back to promoting the oldest
        # personal one, so a household that only ever had personal grocery lists keeps its
        # items (and its history) rather than getting a brand-new empty list beside them.
        canonical_grocery = next((row for row in grocery_rows if row.owner_person_id is None), None)
        if canonical_grocery is None and grocery_rows:
            canonical_grocery = grocery_rows[0]
            canonical_grocery.owner_person = None
            canonical_grocery.title = "Grocery"
            canonical_grocery.updated_at = now
            canonical_grocery.save(update_fields=["owner_person", "title", "updated_at"])
        if canonical_grocery is None:
            canonical_grocery = AtlasList.objects.create(
                household=household, title="Grocery", list_type="grocery",
                created_at=now, updated_at=now,
            )
        retire_into(canonical_grocery, grocery_rows)

        # --- To-dos: Household + one per active Person -------------------------------------
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
        active_person_ids = set()
        for person in Person.objects.filter(household=household, deleted_at__isnull=True):
            active_person_ids.add(person.id)
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

        # A personal To-do list whose owner was deleted has no place in the product, but its
        # items are still real household work. Move them to Household rather than leaving them
        # on a list nobody can reach.
        retire_into(
            canonical_household_todo,
            list(
                AtlasList.objects.filter(
                    household=household, list_type="todo", deleted_at__isnull=True,
                ).exclude(owner_person__isnull=True).exclude(owner_person_id__in=active_person_ids)
            ),
        )

        # --- Grocery is assignee-free, including anything merged in above ------------------
        for item in AtlasListItem.objects.filter(atlas_list=canonical_grocery):
            item.assigned_to_people.clear()

        # --- Reminders become To-dos, and stop being reminders ------------------------------
        for reminder in AtlasReminder.objects.filter(household=household, deleted_at__isnull=True):
            assignee_ids = list(reminder.assigned_to_people.values_list("id", flat=True))
            target_list = canonical_household_todo
            if len(assignee_ids) == 1 and assignee_ids[0] in person_todo_by_person:
                target_list = person_todo_by_person[assignee_ids[0]]

            item = AtlasListItem.objects.create(
                household=household, atlas_list=target_list, title=reminder.title,
                notes=_notes_for(reminder), due_at=reminder.due_at, is_all_day=reminder.is_all_day,
                notify_offsets=_notify_offsets_for(reminder), position=0,
                created_at=reminder.created_at, updated_at=now,
            )
            if assignee_ids:
                item.assigned_to_people.set(assignee_ids)

            # Hand the existing calendar entry to the To-do instead of creating a second one.
            event = (
                CalendarEvent.objects.filter(pk=reminder.calendar_event_id).first()
                if reminder.calendar_event_id else None
            )
            if event is not None:
                event.source_record_type = "AtlasListItem"
                event.source_record_id = item.id
                event.event_kind = "task"
                event.updated_at = now
                event.save(update_fields=[
                    "source_record_type", "source_record_id", "event_kind", "updated_at",
                ])
                item.calendar_event_id = event.id
                item.save(update_fields=["calendar_event_id"])

            reminder.calendar_event_id = None
            reminder.deleted_at = now
            reminder.updated_at = now
            reminder.save(update_fields=["calendar_event_id", "deleted_at", "updated_at"])


def restructure_reverse(apps, schema_editor):
    # Merges, retirements and reminder-to-to-do conversions are not safely undoable — no data is
    # lost (everything survives as soft-deleted rows or additional to-do items), but reversing
    # would require guessing which lists/items were pre-existing vs. migration-created.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("atlas", "0009_todo_and_grocery_fields"),
        ("people", "0001_initial"),
        ("core", "0001_initial"),
        ("scheduling", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(restructure_forward, restructure_reverse),
    ]
