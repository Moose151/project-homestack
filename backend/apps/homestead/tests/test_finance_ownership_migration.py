from datetime import datetime
from decimal import Decimal

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class HomeFinanceOwnershipMigrationTests(TransactionTestCase):
    migrate_from = [
        ("homestead", "0009_utility_bills"),
        ("solace", "0010_consolidate_subscriptions_into_bills"),
    ]
    migrate_to = [("homestead", "0010_solace_owns_home_finance")]

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        old_apps = executor.loader.project_state(self.migrate_from).apps
        Household = old_apps.get_model("core", "Household")
        Bill = old_apps.get_model("solace", "Bill")
        InsurancePolicy = old_apps.get_model("homestead", "InsurancePolicy")
        HouseholdCost = old_apps.get_model("homestead", "HouseholdCost")
        # A TransactionTestCase truncates every table when it finishes, taking the
        # migration-seeded Household with it, so a migration test cannot assume an
        # earlier one left it in place. Same defensive fixture as apps.solace's.
        household = Household.objects.first() or Household.objects.create(name="Home")
        due_at = timezone.make_aware(datetime(2026, 8, 12, 0, 0))

        linked_bill = Bill.objects.create(
            household_id=household.id,
            name="Contents cover",
            category="insurance",
            amount=Decimal("500.00"),
            source_node="homestead",
            source_record_type="insurance_policy",
            source_record_id=999,
        )
        self.policy_id = InsurancePolicy.objects.create(
            household_id=household.id,
            name="Contents cover",
            provider="Cover Co",
            premium_amount=Decimal("720.00"),
            billing_cycle="yearly",
            next_renewal_at=due_at,
            solace_bill_ref=linked_bill.id,
        ).id
        self.cost_id = HouseholdCost.objects.create(
            household_id=household.id,
            name="Electricity",
            cost_type="electricity",
            provider="Energy Co",
            amount=Decimal("240.00"),
            billing_cycle="quarterly",
            next_due_at=due_at,
        ).id

        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        self.apps = executor.loader.project_state(self.migrate_to).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_existing_home_records_are_linked_to_solace_owned_bills(self):
        Bill = self.apps.get_model("solace", "Bill")
        InsurancePolicy = self.apps.get_model("homestead", "InsurancePolicy")
        HouseholdCost = self.apps.get_model("homestead", "HouseholdCost")

        policy = InsurancePolicy.objects.get(pk=self.policy_id)
        policy_bill = Bill.objects.get(pk=policy.solace_bill_ref)
        self.assertEqual(policy_bill.amount, Decimal("720.00"))
        self.assertEqual(policy_bill.source_node, "homestead")
        self.assertEqual(policy_bill.source_record_type, "insurance_policy")
        self.assertEqual(policy_bill.source_record_id, policy.id)

        cost = HouseholdCost.objects.get(pk=self.cost_id)
        cost_bill = Bill.objects.get(pk=cost.solace_bill_ref)
        self.assertEqual(cost_bill.name, "Electricity")
        self.assertEqual(cost_bill.amount, Decimal("240.00"))
        self.assertEqual(cost_bill.recurrence_rule, "FREQ=MONTHLY;INTERVAL=3")
        self.assertEqual(cost_bill.source_record_type, "household_cost")
        self.assertEqual(cost_bill.source_record_id, cost.id)
