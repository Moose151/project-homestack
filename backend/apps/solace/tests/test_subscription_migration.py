from datetime import datetime
from decimal import Decimal

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class SubscriptionConsolidationMigrationTests(TransactionTestCase):
    migrate_from = [
        ("scheduling", "0003_multi_person_assignment"),
        ("solace", "0009_income_scope_and_allocations"),
    ]
    migrate_to = [
        ("scheduling", "0003_multi_person_assignment"),
        ("solace", "0010_consolidate_subscriptions_into_bills"),
    ]

    def setUp(self):
        super().setUp()
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_from)
        old_apps = self.executor.loader.project_state(self.migrate_from).apps
        Household = old_apps.get_model("core", "Household")
        CalendarEvent = old_apps.get_model("scheduling", "CalendarEvent")
        Subscription = old_apps.get_model("solace", "Subscription")

        household = Household.objects.first() or Household.objects.create(name="Home")
        renewal = timezone.make_aware(datetime(2026, 9, 15, 9))
        event = CalendarEvent.objects.create(
            household_id=household.pk,
            title="Subscription: Streaming",
            start_at=renewal,
            is_all_day=True,
            recurrence_rule="FREQ=MONTHLY",
            source_record_type="Subscription",
            source_record_id=1,
            colour="#426e9b",
            visibility="sensitive",
            sensitivity="financial",
        )
        self.subscription_id = Subscription.objects.create(
            household_id=household.pk,
            name="Streaming",
            provider="Example Media",
            amount=Decimal("19.99"),
            billing_cycle="monthly",
            next_renewal_at=renewal,
            is_all_day=True,
            recurrence_rule="FREQ=MONTHLY",
            is_active=True,
            notes="Family plan",
            calendar_event_id=event.pk,
            visibility="sensitive",
            sensitivity="financial",
        ).pk
        self.event_id = event.pk

        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)
        self.apps = self.executor.loader.project_state(self.migrate_to).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_existing_subscription_becomes_a_bill_and_keeps_its_calendar_link(self):
        Bill = self.apps.get_model("solace", "Bill")
        CalendarEvent = self.apps.get_model("scheduling", "CalendarEvent")

        bill = Bill.objects.get(name="Streaming")
        self.assertEqual(bill.category, "subscription")
        self.assertEqual(bill.provider, "Example Media")
        self.assertEqual(bill.amount, Decimal("19.99"))
        self.assertEqual(bill.due_at.date().isoformat(), "2026-09-15")
        self.assertEqual(bill.recurrence_rule, "FREQ=MONTHLY")
        self.assertTrue(bill.include_in_set_aside)
        self.assertEqual(bill.calendar_event_id, self.event_id)

        event = CalendarEvent.objects.get(pk=self.event_id)
        self.assertEqual(event.title, "Bill: Streaming")
        self.assertEqual(event.source_record_type, "Bill")
        self.assertEqual(event.source_record_id, bill.pk)
        self.assertEqual(event.colour, "#8f4e38")
