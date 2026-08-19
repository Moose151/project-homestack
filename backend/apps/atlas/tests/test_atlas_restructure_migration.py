"""atlas.0010 — the v0.40 restructure must adapt existing data, not orphan it.

Two failure modes these tests exist to prevent, both of which would only ever show up on a
household that had been using Atlas for a while:

1. **Stranded grocery.** "One Grocery list per household" was originally implemented by merging
   only the lists with no ``owner_person``. A household that had per-person grocery lists would
   have kept them — still active, still holding items, but outside the one list the Grocery tab
   shows. Nothing would have told them the items were gone.

2. **Doubled reminders.** Copying an ``AtlasReminder`` into a To-do while leaving the reminder
   active gives the same thing two owners: the reminder's calendar event is swept by
   ``run_due_reminders`` while the new To-do's ``notify_offsets`` are swept by
   ``run_due_todo_offsets``, and both the reminder and the item render on the calendar.
"""
from datetime import datetime, timedelta

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

# Only atlas moves. Every other app stays on its current leaf, so the executor gets a plan of
# purely-backwards then purely-forwards steps rather than a mixed one it refuses to run.
BEFORE = [("atlas", "0009_todo_and_grocery_fields")]
AFTER = [("atlas", "0010_atlas_restructure_data")]


class AtlasRestructureMigrationTests(TransactionTestCase):
    # Note for anyone adding another migration test: a TransactionTestCase truncates every table
    # when it finishes, which takes the Household and Node rows the data migrations seeded with
    # it. This file sorts first among the three migration test cases, so the ones after it must
    # not assume that seed is still present — they build their own (see apps.homestead's and
    # apps.solace's fixtures).

    def _migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def setUp(self):
        super().setUp()
        # atlas.0010 changes data, not schema, so the live models already match the table shape
        # at 0009 and can be used to build the "before" fixtures directly.
        self._migrate(BEFORE)
        from apps.atlas.models import AtlasList, AtlasListItem, AtlasReminder
        from apps.core.models import Household
        from apps.people.models import Person
        from apps.scheduling.models import CalendarEvent

        self.household = Household.objects.first() or Household.objects.create(name="Home")
        now = timezone.now()

        self.mum = Person.objects.create(household=self.household, display_name="Mum")
        self.kid = Person.objects.create(household=self.household, display_name="Kid")
        self.gone = Person.objects.create(
            household=self.household, display_name="Moved out", deleted_at=now,
        )

        def make_list(title, list_type, owner=None, created_at=None):
            return AtlasList.objects.create(
                household=self.household, title=title, list_type=list_type,
                owner_person=owner, created_at=created_at or now, updated_at=now,
            )

        # Two household grocery lists AND two personal ones, each with an item.
        self.shared_grocery = make_list(
            "Grocery", "grocery", created_at=now - timedelta(days=30),
        )
        self.second_shared_grocery = make_list(
            "Aldi", "grocery", created_at=now - timedelta(days=20),
        )
        self.mum_grocery = make_list(
            "Mum's shopping", "grocery", owner=self.mum, created_at=now - timedelta(days=10),
        )
        self.kid_grocery = make_list(
            "Kid's snacks", "grocery", owner=self.kid, created_at=now - timedelta(days=5),
        )
        for atlas_list, title in (
            (self.shared_grocery, "Milk"),
            (self.second_shared_grocery, "Bread"),
            (self.mum_grocery, "Coffee"),
            (self.kid_grocery, "Biscuits"),
        ):
            item = AtlasListItem.objects.create(
                household=self.household, atlas_list=atlas_list, title=title,
            )
            # Grocery becomes assignee-free; every one of these must end up cleared.
            item.assigned_to_people.set([self.mum.pk])

        # A personal To-do list belonging to someone who has since been deleted.
        self.gone_todos = make_list("Moved out", "todo", owner=self.gone)
        AtlasListItem.objects.create(
            household=self.household, atlas_list=self.gone_todos, title="Return the key",
        )

        # A legacy shopping list, which becomes an ordinary Lists & Notes checklist.
        self.legacy_shopping = make_list("Hardware", "shopping")

        # A dated reminder with a real calendar entry, assigned to one person.
        due = timezone.make_aware(datetime(2026, 12, 24, 18, 0))
        event = CalendarEvent.objects.create(
            household=self.household, title="Collect the turkey", start_at=due,
            source_record_type="AtlasReminder", source_record_id=0, event_kind="event",
        )
        reminder = AtlasReminder.objects.create(
            household=self.household, title="Collect the turkey", body="Ask for the big one",
            due_at=due, is_all_day=False, notifications_enabled=True, calendar_event_id=event.pk,
        )
        reminder.assigned_to_people.set([self.mum.pk])
        event.source_record_id = reminder.pk
        event.save(update_fields=["source_record_id"])
        self.reminder_id = reminder.pk
        self.event_id = event.pk

        # An all-day reminder with notifications off — it must not gain any offsets.
        self.quiet_reminder_id = AtlasReminder.objects.create(
            household=self.household, title="Bin night", due_at=due, is_all_day=True,
            notifications_enabled=False,
        ).pk

        # A reminder falling inside the schedulers' live windows, so the duplication test below
        # exercises them for real rather than against a date nothing would ever sweep. Its
        # 1-day-before offset and the fixed 24h calendar lead both land on this one run.
        from apps.accounts.models import User
        self.recipient = User.objects.create_user(
            username="migrated-recipient", display_name="Recipient", role=User.Role.ADMIN,
            password="test-pass-123",
        )
        AtlasReminder.objects.create(
            household=self.household, title="Due tomorrow job",
            due_at=timezone.now() + timedelta(hours=24), is_all_day=False,
            notifications_enabled=True,
        )

        self._migrate(AFTER)

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    # --- helpers ----------------------------------------------------------------------------

    def _lists(self, **filters):
        """Active lists only — AtlasList.objects already excludes soft-deleted rows."""
        from apps.atlas.models import AtlasList
        return AtlasList.objects.filter(household=self.household, **filters)

    def _migrated_item(self, title="Collect the turkey"):
        from apps.atlas.models import AtlasListItem
        return AtlasListItem.objects.get(title=title)

    # --- grocery ----------------------------------------------------------------------------

    def test_grocery_folds_into_one_shared_list_with_every_item(self):
        """Every grocery list folds into one shared list, and no item is left behind on a
        personal one — which is the failure this migration was rewritten to prevent."""
        from apps.atlas.models import AtlasList

        active = list(self._lists(list_type="grocery"))
        self.assertEqual(len(active), 1, [row.title for row in active])
        canonical = active[0]
        self.assertIsNone(canonical.owner_person_id, "the survivor must be a household list")

        self.assertEqual(
            sorted(canonical.items.values_list("title", flat=True)),
            ["Biscuits", "Bread", "Coffee", "Milk"],
            "items from the personal grocery lists must arrive on the shared list",
        )

        # Retired, not destroyed.
        for old_id in (self.second_shared_grocery.pk, self.mum_grocery.pk, self.kid_grocery.pk):
            row = AtlasList.all_objects.get(pk=old_id)
            self.assertIsNotNone(row.deleted_at, f"{row.title} should be soft-deleted")

        # Grocery is assignee-free (D19 §C), including everything merged in.
        for item in canonical.items.all():
            self.assertEqual(list(item.assigned_to_people.all()), [], item.title)

    # --- to-dos -----------------------------------------------------------------------------

    def test_todo_lists_are_rebuilt_and_legacy_lists_folded_in(self):
        from apps.atlas.models import AtlasList

        todo_lists = self._lists(list_type="todo")
        self.assertEqual(todo_lists.filter(owner_person__isnull=True).count(), 1)
        self.assertEqual(
            set(todo_lists.filter(owner_person__isnull=False).values_list("owner_person_id", flat=True)),
            {self.mum.pk, self.kid.pk},
            "one personal list per active Person, and none for the deleted one",
        )

        # The deleted person's list is retired, but their outstanding work is not stranded.
        self.assertIsNotNone(AtlasList.all_objects.get(pk=self.gone_todos.pk).deleted_at)
        household_list = todo_lists.filter(owner_person__isnull=True).get()
        self.assertIn("Return the key", household_list.items.values_list("title", flat=True))

        # Legacy shopping/wishlist lists become ordinary Lists & Notes checklists.
        self.assertEqual(AtlasList.objects.get(pk=self.legacy_shopping.pk).list_type, "checklist")

    # --- reminders --------------------------------------------------------------------------

    def test_a_reminder_becomes_one_usable_todo_carrying_its_notification_intent(self):
        from apps.atlas.models import AtlasListItem

        items = AtlasListItem.objects.filter(title="Collect the turkey")
        self.assertEqual(items.count(), 1)
        item = items.get()
        self.assertEqual(item.notes, "Ask for the big one")
        self.assertIsNotNone(item.due_at)
        # One named assignee means their personal list, not the shared one.
        self.assertEqual(item.atlas_list.owner_person_id, self.mum.pk)
        self.assertEqual(item.atlas_list.list_type, "todo")
        # The old fixed leads, expressed as offsets.
        self.assertEqual(item.notify_offsets, [0, 1440])

        # Notifications were off on this one, so it must stay silent.
        self.assertEqual(self._migrated_item("Bin night").notify_offsets, [])

    def test_a_migrated_reminder_leaves_exactly_one_calendar_entry(self):
        """The reminder's existing event is handed to the To-do, not duplicated beside it."""
        from apps.atlas.models import AtlasReminder
        from apps.scheduling.models import CalendarEvent

        reminder = AtlasReminder.all_objects.get(pk=self.reminder_id)
        self.assertIsNotNone(reminder.deleted_at, "the row must survive as archival data")
        self.assertIsNone(
            reminder.calendar_event_id,
            "a retired reminder must not still claim a calendar entry",
        )

        events = CalendarEvent.objects.filter(title="Collect the turkey")
        self.assertEqual(events.count(), 1)
        event = events.get()
        self.assertEqual(event.pk, self.event_id, "the original row is reused, not replaced")
        self.assertEqual(event.source_record_type, "AtlasListItem")
        self.assertEqual(event.source_record_id, self._migrated_item().pk)
        self.assertEqual(self._migrated_item().calendar_event_id, event.pk)

        self.assertFalse(
            CalendarEvent.all_objects.filter(source_record_type="AtlasReminder").exists(),
            "no calendar entry may still point at a retired reminder",
        )

    def test_a_migrated_reminder_notifies_once_not_twice(self):
        """The end-to-end proof, run against genuinely migrated rows.

        Both schedulers are run over the same migrated item. Before this migration was
        corrected, ``run_due_reminders`` would have notified for the still-live reminder's
        calendar event *and* ``run_due_todo_offsets`` for the new To-do's 1-day-before offset —
        two notifications, and two ledger entries, for one household job.
        """
        from apps.notifications.models import Notification, NotificationReminderLog
        from apps.notifications.tasks import run_due_reminders, run_due_todo_offsets

        item = self._migrated_item("Due tomorrow job")
        self.assertEqual(item.notify_offsets, [0, 1440])

        run_due_reminders()
        run_due_todo_offsets()
        run_due_reminders()      # re-running must never add a second copy
        run_due_todo_offsets()

        self.assertEqual(
            Notification.objects.filter(message="Due tomorrow job").count(), 1,
            "one To-do plus one due offset must mean exactly one notification",
        )
        self.assertEqual(
            NotificationReminderLog.objects.filter(
                record_type="AtlasListItem", record_id=item.pk,
            ).count(),
            1,
        )
        self.assertFalse(
            NotificationReminderLog.objects.filter(record_type="CalendarEvent").exists(),
            "the fixed calendar sweep must not claim a To-do's occurrence as well",
        )
