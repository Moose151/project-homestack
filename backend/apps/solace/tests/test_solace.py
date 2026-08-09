"""Solace tests — native finance node. Permission tests first (D10)."""
import io
import sqlite3
import tempfile
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.core.management import CommandError, call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.core.models import get_active_household
from apps.hub.services import get_hub_widgets
from apps.homestead.models import HouseholdCost, InsurancePolicy, MaintenanceTask, ServiceProvider
from apps.notifications.models import Notification
from apps.scheduling.models import CalendarEvent
from apps.solace.services import (
    create_bill,
    create_bucket,
    create_payday,
    create_purchase,
    create_subscription,
    delete_bill,
    mark_bill_paid,
)
from apps.solace.bill_schedule import annual_cost, fortnightly_cost, occurrence_datetimes
from apps.solace.models import (
    AccountBalanceSnapshot,
    Bill,
    BillOccurrence,
    BudgetBucket,
    CycleCloseout,
    FinanceCategory,
    Payday,
    PaydayChecklistItem,
    PaydayChecklistPreference,
    PlannedPurchase,
    SolaceSettings,
    Subscription,
)
from apps.solace.services import update_bill
from apps.solace.tasks import send_due_reminders


def _make_user(username, role=User.Role.ADMIN, is_child=False) -> User:
    user = User.objects.create_user(
        username=username, display_name=username.capitalize(), role=role, password="pass123!"
    )
    user.set_pin("1234")
    user.is_child_account = is_child
    user.save()
    return user


def _login(client, username, pin="1234"):
    client.post(
        reverse("auth-pin-login"),
        {"username": username, "pin": pin},
        content_type="application/json",
    )


def _reauth(client, password="pass123!"):
    client.post(reverse("auth-reauth"), {"password": password}, content_type="application/json")


def _future(days=5):
    return timezone.now() + timezone.timedelta(days=days)


class SolacePermissionTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        self.manager = _make_user("manager", User.Role.MANAGER)
        self.child = _make_user("child", User.Role.USER, is_child=True)
        self.url = reverse("solace-bill-list")

    def test_unauthenticated_rejected(self):
        self.assertIn(self.client.get(self.url).status_code, [401, 403])

    def test_admin_requires_reauth(self):
        _login(self.client, "admin")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_view_after_reauth(self):
        _login(self.client, "admin")
        _reauth(self.client)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_admin_can_view_without_reauth_when_household_setting_is_off(self):
        from apps.nodes.models import HouseholdNode

        HouseholdNode.objects.filter(node__key="solace").update(
            requires_reauthentication=False
        )
        _login(self.client, "admin")
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertTrue(
            AuditLog.objects.filter(action="sensitive_node_accessed").exists()
        )

    def test_manager_not_granted_by_default(self):
        _login(self.client, "manager")
        _reauth(self.client)
        resp = self.client.get(self.url)
        self.assertIn(resp.status_code, [401, 403])

    def test_child_cannot_reauth_or_view(self):
        _login(self.client, "child")
        _reauth(self.client)
        resp = self.client.get(self.url)
        self.assertIn(resp.status_code, [401, 403])

    def test_bill_timeline_requires_solace_access_and_reauth(self):
        bill = create_bill(self.admin, name="Protected history", due_at=_future())
        url = reverse("solace-bill-occurrences", args=[bill.id])
        _login(self.client, "manager")
        _reauth(self.client)
        self.assertIn(self.client.get(url).status_code, [401, 403])

    def test_balance_forecast_requires_solace_access_and_reauth(self):
        _login(self.client, "manager")
        _reauth(self.client)
        self.assertIn(
            self.client.get(reverse("solace-forecast")).status_code,
            [401, 403],
        )


class SolaceCrudAndCalendarTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        _login(self.client, "admin")
        _reauth(self.client)

    def test_bill_crud_defaults_financial(self):
        resp = self.client.post(
            reverse("solace-bill-list"),
            {"name": "Electricity", "amount": "120.50", "due_at": _future().isoformat()},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["visibility"], "sensitive")
        self.assertEqual(resp.json()["sensitivity"], "financial")
        self.assertIsNotNone(resp.json()["calendar_event_id"])

    def test_bill_rejects_unknown_homestead_destination(self):
        resp = self.client.post(
            reverse("solace-bill-list"),
            {"name": "Mystery home bill", "home_destination": "unknown"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(Bill.objects.filter(name="Mystery home bill").exists())

    def test_home_insurance_bill_creates_one_linked_homestead_policy(self):
        renewal = _future()
        resp = self.client.post(
            reverse("solace-bill-list"),
            {
                "name": "Home and contents",
                "provider": "Cover Co",
                "category": "insurance",
                "amount": "1450.25",
                "due_at": renewal.isoformat(),
                "recurrence_rule": "FREQ=YEARLY",
                "home_destination": "insurance_policy",
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        bill = Bill.objects.get(pk=resp.json()["id"])
        policy = InsurancePolicy.objects.get(solace_bill_ref=bill.id)
        self.assertEqual(bill.source_node, "homestead")
        self.assertEqual(bill.source_record_type, "insurance_policy")
        self.assertEqual(bill.source_record_id, policy.id)
        self.assertEqual(policy.name, "Home and contents")
        self.assertEqual(policy.provider, "Cover Co")
        self.assertEqual(str(policy.premium_amount), "1450.25")
        self.assertEqual(policy.billing_cycle, "yearly")
        self.assertEqual(InsurancePolicy.objects.count(), 1)
        self.assertEqual(Bill.objects.count(), 1)

    def test_home_service_bill_creates_linked_household_cost(self):
        resp = self.client.post(
            reverse("solace-bill-list"),
            {
                "name": "Electricity",
                "provider": "Energy Co",
                "category": "utilities",
                "amount": "220.00",
                "due_at": _future().isoformat(),
                "recurrence_rule": "FREQ=MONTHLY;INTERVAL=3",
                "home_destination": "household_cost",
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        bill = Bill.objects.get(pk=resp.json()["id"])
        cost = HouseholdCost.objects.get(solace_bill_ref=bill.id)
        self.assertEqual(cost.cost_type, "electricity")
        self.assertEqual(cost.billing_cycle, "quarterly")
        self.assertEqual(bill.source_record_type, "household_cost")
        self.assertEqual(bill.source_record_id, cost.id)

    def test_paid_home_maintenance_bill_creates_task_and_provider_without_duplicate_calendar(self):
        due_at = _future()
        resp = self.client.post(
            reverse("solace-bill-list"),
            {
                "name": "Annual aircon service",
                "provider": "Cool Air Co",
                "category": "other",
                "amount": "180.00",
                "due_at": due_at.isoformat(),
                "recurrence_rule": "FREQ=YEARLY",
                "home_destination": "maintenance",
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        bill = Bill.objects.get(pk=resp.json()["id"])
        task = MaintenanceTask.objects.get(solace_bill_ref=bill.id)
        self.assertEqual(task.provider.name, "Cool Air Co")
        self.assertEqual(ServiceProvider.objects.filter(name="Cool Air Co").count(), 1)
        self.assertEqual(bill.source_record_type, "maintenance")
        self.assertEqual(bill.source_record_id, task.id)
        self.assertIsNone(task.calendar_event_id)
        self.assertEqual(
            CalendarEvent.objects.filter(
                source_node__key="homestead", source_record_id=task.id
            ).count(),
            0,
        )
        self.assertEqual(CalendarEvent.objects.filter(pk=bill.calendar_event_id).count(), 1)

    def test_existing_bill_can_be_organised_once_without_retyping(self):
        bill = create_bill(
            self.admin,
            name="Council rates",
            category="council",
            amount="600.00",
            due_at=_future(),
            recurrence_rule="FREQ=MONTHLY;INTERVAL=3",
        )
        url = reverse("solace-bill-detail", args=[bill.id])
        first = self.client.patch(
            url,
            {"home_destination": "household_cost"},
            content_type="application/json",
        )
        second = self.client.patch(
            url,
            {"home_destination": "household_cost"},
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        bill.refresh_from_db()
        cost = HouseholdCost.objects.get(solace_bill_ref=bill.id)
        self.assertEqual(cost.cost_type, "rates")
        self.assertEqual(HouseholdCost.objects.count(), 1)
        self.assertEqual(bill.source_record_id, cost.id)

    def test_linked_bill_details_cannot_diverge_from_homestead(self):
        created = self.client.post(
            reverse("solace-bill-list"),
            {
                "name": "Building cover",
                "category": "insurance",
                "amount": "900.00",
                "home_destination": "insurance_policy",
            },
            content_type="application/json",
        )
        bill_id = created.json()["id"]
        url = reverse("solace-bill-detail", args=[bill_id])
        changed = self.client.patch(
            url,
            {"amount": "1.00"},
            content_type="application/json",
        )
        removed = self.client.delete(url)
        self.assertEqual(changed.status_code, 400)
        self.assertEqual(removed.status_code, 400)
        self.assertEqual(str(Bill.objects.get(pk=bill_id).amount), "900.00")
        self.assertEqual(
            str(InsurancePolicy.objects.get(solace_bill_ref=bill_id).premium_amount),
            "900.00",
        )

    def test_mark_bill_paid_removes_calendar_event(self):
        bill = create_bill(self.admin, name="Rates", amount="900.00", due_at=_future())
        event_id = bill.calendar_event_id
        resp = self.client.post(reverse("solace-bill-paid", args=[bill.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["is_paid"])
        self.assertFalse(CalendarEvent.objects.filter(pk=event_id).exists())

    def test_delete_bill_deletes_calendar_event(self):
        bill = create_bill(self.admin, name="Water", due_at=_future())
        event_id = bill.calendar_event_id
        delete_bill(self.admin, bill)
        self.assertFalse(CalendarEvent.objects.filter(pk=event_id).exists())

    def test_bucket_and_purchase_progress(self):
        bucket = create_bucket(self.admin, name="Emergency fund", target_amount="1000.00", current_amount="250.00")
        self.assertEqual(bucket.progress_percent, 25)
        purchase = create_purchase(self.admin, name="Sofa", target_amount="800.00", saved_amount="200.00")
        self.assertEqual(purchase.remaining_amount, 600)

    def test_subscription_creates_financial_event(self):
        sub = create_subscription(self.admin, name="Streaming", amount="12.99", next_renewal_at=_future())
        event = CalendarEvent.objects.get(pk=sub.calendar_event_id)
        self.assertEqual(event.source_node.key, "solace")
        self.assertEqual(event.sensitivity, "financial")

    def test_payday_exposes_known_anchor_and_calculated_upcoming_date(self):
        anchor = _future(2)
        create_payday(
            self.admin,
            title="Weekly income",
            expected_amount="1000.00",
            pay_at=anchor,
            recurrence_rule="FREQ=WEEKLY",
        )
        row = self.client.get(reverse("solace-payday-list")).json()[0]
        self.assertEqual(row["pay_at"], anchor.isoformat().replace("+00:00", "Z"))
        self.assertEqual(
            datetime.fromisoformat(row["next_pay_at"].replace("Z", "+00:00")),
            anchor.replace(microsecond=0),
        )

    def test_monthly_occurrences_clamp_to_month_end_without_drifting(self):
        bill = create_bill(
            self.admin,
            name="Month end",
            amount="100.00",
            due_at=timezone.make_aware(datetime(2027, 1, 31, 9)),
            recurrence_rule="FREQ=MONTHLY;BYMONTHDAY=31",
        )
        values = occurrence_datetimes(
            bill,
            date(2027, 1, 1),
            date(2027, 4, 30),
        )
        self.assertEqual(
            [timezone.localdate(value).isoformat() for value in values],
            ["2027-01-31", "2027-02-28", "2027-03-31", "2027-04-30"],
        )
        self.assertEqual(annual_cost(bill), 1200)
        self.assertEqual(str(fortnightly_cost(bill)), "46.15")

    def test_bill_stop_after_bounds_occurrences_and_metadata_round_trips(self):
        due_at = timezone.make_aware(datetime(2027, 1, 1, 9))
        response = self.client.post(
            reverse("solace-bill-list"),
            {
                "name": "Fixed term",
                "amount": "50.00",
                "due_at": due_at.isoformat(),
                "recurrence_rule": "FREQ=MONTHLY",
                "end_date": "2027-03-01",
                "is_autopay": True,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["is_autopay"])
        self.assertEqual(response.json()["end_date"], "2027-03-01")
        bill = Bill.objects.get(name="Fixed term")
        values = occurrence_datetimes(bill, date(2027, 1, 1), date(2027, 6, 30))
        self.assertEqual(
            [timezone.localdate(value).isoformat() for value in values],
            ["2027-01-01", "2027-02-01", "2027-03-01"],
        )

        invalid = self.client.patch(
            reverse("solace-bill-detail", args=[bill.id]),
            {"end_date": "2026-12-31"},
            content_type="application/json",
        )
        self.assertEqual(invalid.status_code, 400)

    def test_bill_timeline_returns_upcoming_and_recent_history(self):
        bill = create_bill(
            self.admin,
            name="Timeline bill",
            amount="25.00",
            due_at=timezone.now() - timedelta(days=84),
            recurrence_rule="FREQ=WEEKLY",
        )
        response = self.client.get(
            reverse("solace-bill-occurrences", args=[bill.id])
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["bill"]["name"], "Timeline bill")
        self.assertEqual(len(data["upcoming"]), 12)
        self.assertEqual(len(data["history"]), 12)
        self.assertLess(
            data["upcoming"][0]["due_at"],
            data["upcoming"][-1]["due_at"],
        )
        self.assertGreater(
            data["history"][0]["due_at"],
            data["history"][-1]["due_at"],
        )

    def test_recurring_occurrence_can_be_paid_restored_and_skipped(self):
        bill = create_bill(
            self.admin,
            name="Weekly bill",
            amount="25.00",
            due_at=timezone.now() + timedelta(days=1),
            recurrence_rule="FREQ=WEEKLY",
        )
        occurrence = bill.occurrences.first()
        event_id = bill.calendar_event_id
        paid = self.client.post(
            reverse("solace-occurrence-action", args=[occurrence.id, "paid"])
        )
        self.assertEqual(paid.status_code, 200)
        self.assertEqual(paid.json()["status"], "paid")
        self.assertTrue(CalendarEvent.objects.filter(pk=event_id).exists())

        unpaid = self.client.post(
            reverse("solace-occurrence-action", args=[occurrence.id, "unpaid"])
        )
        self.assertEqual(unpaid.json()["status"], "upcoming")
        skipped = self.client.post(
            reverse("solace-occurrence-action", args=[occurrence.id, "skip"])
        )
        self.assertEqual(skipped.json()["status"], "skipped")

    def test_bill_edit_refreshes_future_unpaid_occurrences_only(self):
        bill = create_bill(
            self.admin,
            name="Changing bill",
            amount="100.00",
            due_at=timezone.now() + timedelta(days=1),
            recurrence_rule="FREQ=WEEKLY",
        )
        first, second = list(bill.occurrences.all()[:2])
        self.client.post(reverse("solace-occurrence-action", args=[first.id, "paid"]))
        update_bill(self.admin, bill, amount="125.00")
        first.refresh_from_db()
        self.assertEqual(first.status, "paid")
        self.assertEqual(first.amount, 100)
        refreshed_second = BillOccurrence.objects.filter(
            bill=bill,
            due_at=second.due_at,
        ).get()
        self.assertEqual(refreshed_second.amount, 125)

    def test_bill_edit_can_refresh_all_unpaid_and_preserve_paid_history(self):
        anchor = timezone.now() - timedelta(days=70)
        bill = create_bill(
            self.admin,
            name="Corrected bill",
            amount="80.00",
            due_at=anchor,
            recurrence_rule="FREQ=MONTHLY",
        )
        past = list(bill.occurrences.filter(due_at__lt=timezone.now()).order_by("due_at"))
        self.assertGreaterEqual(len(past), 2)
        paid, unpaid = past[-2:]
        paid_date = paid.due_at
        unpaid_date = unpaid.due_at
        self.client.post(reverse("solace-occurrence-action", args=[paid.id, "paid"]))

        response = self.client.patch(
            reverse("solace-bill-detail", args=[bill.id]),
            {
                "amount": "95.00",
                "occurrence_update_scope": "all_unpaid",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        preserved = BillOccurrence.objects.get(bill=bill, due_at=paid_date)
        corrected = BillOccurrence.objects.get(bill=bill, due_at=unpaid_date)
        self.assertEqual(preserved.status, BillOccurrence.Status.PAID)
        self.assertEqual(preserved.amount, 80)
        self.assertEqual(corrected.status, BillOccurrence.Status.UPCOMING)
        self.assertEqual(corrected.amount, 95)

    def test_month_schedule_combines_bills_and_income(self):
        create_bill(
            self.admin,
            name="Rent",
            amount="800.00",
            due_at=timezone.make_aware(datetime(2026, 8, 3, 9)),
            recurrence_rule="FREQ=MONTHLY",
        )
        create_payday(
            self.admin,
            title="Household pay",
            expected_amount="2400.00",
            pay_at=timezone.make_aware(datetime(2026, 8, 1, 9)),
            recurrence_rule="FREQ=WEEKLY;INTERVAL=2",
        )
        resp = self.client.get(
            reverse("solace-schedule"),
            {"start": "2026-08-01", "end": "2026-08-31"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["occurrences"][0]["bill_name"], "Rent")
        self.assertEqual(data["summary"]["bills_total"], "800.00")
        self.assertEqual(data["summary"]["income_total"], "7200.00")
        self.assertEqual(len(data["income_events"]), 3)


class SolacePayCyclePlanTests(TestCase):
    def setUp(self):
        self.admin = _make_user("planner", User.Role.ADMIN)
        _login(self.client, "planner")
        _reauth(self.client)
        create_payday(
            self.admin,
            title="Alex pay",
            expected_amount="2000.00",
            pay_at=timezone.make_aware(datetime(2026, 8, 1, 9)),
            recurrence_rule="FREQ=WEEKLY;INTERVAL=2",
        )
        create_payday(
            self.admin,
            title="Sam pay",
            expected_amount="1000.00",
            pay_at=timezone.make_aware(datetime(2026, 8, 2, 9)),
            recurrence_rule="FREQ=WEEKLY;INTERVAL=2",
        )
        self.bills = create_bucket(
            self.admin,
            name="Bills",
            category="Bills",
            allocation_method=BudgetBucket.AllocationMethod.PERCENTAGE,
            allocation_value="25.00",
            rounding_increment="10.00",
            position=10,
        )
        self.savings = create_bucket(
            self.admin,
            name="Savings",
            category="Savings",
            allocation_method=BudgetBucket.AllocationMethod.FIXED,
            allocation_value="300.00",
            rounding_increment="1.00",
            position=20,
        )

    def test_plan_splits_percentage_and_fixed_rules_by_income(self):
        resp = self.client.get(reverse("solace-plan"), {"date": "2026-08-03"})
        self.assertEqual(resp.status_code, 200)
        plan = resp.json()
        self.assertEqual(plan["cycle_start"], "2026-08-01")
        self.assertEqual(plan["cycle_end"], "2026-08-14")
        self.assertEqual(plan["income_total"], "3000.00")
        self.assertEqual(plan["allocated_total"], "1050.00")
        self.assertEqual(plan["remaining"], "1950.00")
        self.assertEqual(
            [(row["bucket_name"], row["amount"]) for row in plan["buckets"]],
            [("Bills", "750.00"), ("Savings", "300.00")],
        )
        self.assertEqual(
            [row["amount"] for row in plan["sources"][0]["allocations"]],
            ["500.00", "200.00"],
        )
        self.assertEqual(
            [row["amount"] for row in plan["sources"][1]["allocations"]],
            ["250.00", "100.00"],
        )

    def test_plan_can_generate_an_idempotent_cycle_checklist(self):
        url = reverse("solace-plan-checklist")
        resp = self.client.post(f"{url}?date=2026-08-03")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 5)
        self.assertEqual(PaydayChecklistItem.objects.count(), 5)
        bills_item = PaydayChecklistItem.objects.get(bucket=self.bills)
        self.assertEqual(bills_item.cycle_start.isoformat(), "2026-08-01")
        self.assertEqual(bills_item.amount_hint, 750)
        bills_item.is_complete = True
        bills_item.save(update_fields=["is_complete"])

        resp = self.client.post(f"{url}?date=2026-08-03")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PaydayChecklistItem.objects.count(), 5)
        bills_item.refresh_from_db()
        self.assertTrue(bills_item.is_complete)

    def test_checklist_can_open_current_and_next_cycles(self):
        url = reverse("solace-plan-checklist")
        current = self.client.post(f"{url}?date=2026-08-03").json()
        following = self.client.post(f"{url}?date=2026-08-16").json()
        self.assertEqual({row["cycle_start"] for row in current}, {"2026-08-01"})
        self.assertEqual({row["cycle_start"] for row in following}, {"2026-08-15"})

        current_rows = self.client.get(
            reverse("solace-checklist-list"),
            {"date": "2026-08-03"},
        ).json()
        following_rows = self.client.get(
            reverse("solace-checklist-list"),
            {"date": "2026-08-16"},
        ).json()
        self.assertEqual({row["cycle_start"] for row in current_rows}, {"2026-08-01"})
        self.assertEqual({row["cycle_start"] for row in following_rows}, {"2026-08-15"})

    def test_invalid_plan_date_is_rejected(self):
        resp = self.client.get(reverse("solace-plan"), {"date": "03/08/2026"})
        self.assertEqual(resp.status_code, 400)

    def test_paused_payday_is_excluded_from_plan_and_calendar(self):
        payday = Payday.objects.get(title="Sam pay")
        resp = self.client.patch(
            reverse("solace-payday-detail", args=[payday.id]),
            {"is_active": False},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(CalendarEvent.objects.filter(pk=payday.calendar_event_id).exists())
        plan = self.client.get(reverse("solace-plan"), {"date": "2026-08-03"}).json()
        self.assertEqual(plan["income_total"], "2000.00")
        self.assertEqual([row["title"] for row in plan["sources"]], ["Alex pay"])

    def test_plan_requires_fresh_password_reauthentication(self):
        self.client.post(reverse("auth-logout"))
        _login(self.client, "planner")
        resp = self.client.get(reverse("solace-plan"), {"date": "2026-08-03"})
        self.assertEqual(resp.status_code, 403)

    def test_future_income_anchor_still_resolves_the_current_cycle(self):
        Payday.objects.all().delete()
        create_payday(
            self.admin,
            title="Future anchor",
            expected_amount="1500.00",
            pay_at=timezone.make_aware(datetime(2026, 9, 12, 9)),
            recurrence_rule="FREQ=WEEKLY;INTERVAL=2",
        )
        plan = self.client.get(reverse("solace-plan"), {"date": "2026-08-03"}).json()
        self.assertLessEqual(date.fromisoformat(plan["cycle_start"]), date(2026, 8, 3))
        self.assertGreaterEqual(date.fromisoformat(plan["cycle_end"]), date(2026, 8, 3))

    def test_configured_cycle_anchor_overrides_income_dates(self):
        self.client.get(reverse("solace-settings"))
        self.client.patch(
            reverse("solace-settings"),
            {"cycle_anchor_date": "2026-07-30"},
            content_type="application/json",
        )

        plan = self.client.get(reverse("solace-plan"), {"date": "2026-08-03"}).json()

        self.assertEqual(plan["cycle_start"], "2026-07-30")
        self.assertEqual(plan["cycle_end"], "2026-08-12")
        self.assertEqual(plan["income_total"], "3000.00")

    def test_plan_reports_required_set_aside_and_bucket_coverage(self):
        self.client.get(reverse("solace-settings"))
        self.client.patch(
            reverse("solace-settings"),
            {"default_buffer_amount": "30.00"},
            content_type="application/json",
        )
        create_bill(
            self.admin,
            name="Monthly cost",
            amount="260.00",
            due_at=timezone.make_aware(datetime(2026, 8, 5, 9)),
            recurrence_rule="FREQ=MONTHLY",
        )
        create_purchase(
            self.admin,
            name="Goal",
            target_amount="260.00",
            saved_amount="60.00",
            target_date=timezone.make_aware(datetime(2026, 8, 15, 9)),
        )
        set_aside = self.client.get(
            reverse("solace-plan"),
            {"date": "2026-08-03"},
        ).json()["set_aside"]
        self.assertEqual(set_aside["recurring_bills"], "120.00")
        self.assertEqual(set_aside["planned_purchases"], "100.00")
        self.assertEqual(set_aside["buffer"], "30.00")
        self.assertEqual(set_aside["required_total"], "250.00")
        self.assertEqual(set_aside["bills_bucket_total"], "750.00")
        self.assertTrue(set_aside["is_covered"])


class SolaceManagementTests(TestCase):
    def setUp(self):
        self.admin = _make_user("finance-admin", User.Role.ADMIN)
        _login(self.client, "finance-admin")
        _reauth(self.client)

    def test_settings_can_be_created_and_updated(self):
        response = self.client.get(reverse("solace-settings"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["payday_bill_handling"], "new_cycle")
        response = self.client.patch(
            reverse("solace-settings"),
            {
                "currency_symbol": "A$",
                "budget_year": 2027,
                "cycle_anchor_date": "2026-08-01",
                "default_buffer_amount": "500.00",
                "payday_bill_handling": "previous_cycle",
                "show_help_tips": False,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["currency_symbol"], "A$")
        self.assertEqual(response.json()["cycle_anchor_date"], "2026-08-01")
        self.assertEqual(SolaceSettings.objects.count(), 1)

    def test_cycle_anchor_keeps_planning_available_before_income_is_added(self):
        self.client.get(reverse("solace-settings"))
        self.client.patch(
            reverse("solace-settings"),
            {"cycle_anchor_date": "2026-08-01"},
            content_type="application/json",
        )
        plan = self.client.get(reverse("solace-plan"), {"date": "2026-08-03"}).json()
        self.assertEqual(plan["cycle_start"], "2026-08-01")
        self.assertEqual(plan["cycle_end"], "2026-08-14")
        self.assertEqual(plan["sources"], [])

    def test_category_rename_updates_existing_records_and_delete_uses_fallback(self):
        category = FinanceCategory.objects.create(
            household=get_active_household(),
            name="Custom",
            category_type="both",
            created_by=self.admin,
            updated_by=self.admin,
        )
        bill = create_bill(self.admin, name="Custom bill", category="Custom")
        purchase = create_purchase(self.admin, name="Custom purchase", category="Custom")
        response = self.client.patch(
            reverse("solace-category-detail", args=[category.id]),
            {"name": "Renamed"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        bill.refresh_from_db()
        purchase.refresh_from_db()
        self.assertEqual(bill.category, "Renamed")
        self.assertEqual(purchase.category, "Renamed")

        response = self.client.delete(reverse("solace-category-detail", args=[category.id]))
        self.assertEqual(response.status_code, 204)
        bill.refresh_from_db()
        purchase.refresh_from_db()
        self.assertEqual(bill.category, "other")
        self.assertEqual(purchase.category, "other")

    def test_balance_projection_and_cycle_closeout(self):
        create_payday(
            self.admin,
            title="Pay",
            expected_amount="2000.00",
            pay_at=timezone.make_aware(datetime(2026, 8, 1, 9)),
            recurrence_rule="FREQ=WEEKLY;INTERVAL=2",
        )
        create_bill(
            self.admin,
            name="Rent",
            amount="800.00",
            due_at=timezone.make_aware(datetime(2026, 8, 3, 9)),
            recurrence_rule="FREQ=MONTHLY",
        )
        response = self.client.post(
            reverse("solace-balance-list"),
            {"snapshot_date": "2026-08-02", "balance": "2500.00"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(AccountBalanceSnapshot.objects.count(), 1)
        response = self.client.get(reverse("solace-closeout"), {"date": "2026-08-03"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["summary"]["unpaid_total"], "800.00")
        self.assertEqual(response.json()["projected_balance"], "1700.00")

        response = self.client.post(
            f"{reverse('solace-closeout')}?date=2026-08-03",
            {"action": "close", "notes": "Reconciled"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "closed")
        self.assertEqual(CycleCloseout.objects.get().notes, "Reconciled")

        response = self.client.post(
            f"{reverse('solace-closeout')}?date=2026-08-03",
            {"action": "reopen"},
            content_type="application/json",
        )
        self.assertEqual(response.json()["status"], "open")

    def test_balance_forecast_finds_withdrawable_surplus_and_low_point(self):
        self.client.get(reverse("solace-settings"))
        self.client.patch(
            reverse("solace-settings"),
            {"default_buffer_amount": "100.00"},
            content_type="application/json",
        )
        create_payday(
            self.admin,
            title="Household pay",
            expected_amount="1000.00",
            pay_at=timezone.make_aware(datetime(2026, 8, 15, 9)),
            recurrence_rule="FREQ=WEEKLY;INTERVAL=2",
        )
        create_bucket(
            self.admin,
            name="Bills account",
            category="Bills",
            allocation_method=BudgetBucket.AllocationMethod.PERCENTAGE,
            allocation_value="20.00",
            rounding_increment="1.00",
        )
        create_bill(
            self.admin,
            name="Rent",
            amount="600.00",
            due_at=timezone.make_aware(datetime(2026, 8, 10, 9)),
            recurrence_rule="FREQ=MONTHLY",
        )
        create_subscription(
            self.admin,
            name="Streaming",
            amount="50.00",
            next_renewal_at=timezone.make_aware(datetime(2026, 8, 20, 9)),
            recurrence_rule="FREQ=MONTHLY",
        )
        self.client.post(
            reverse("solace-balance-list"),
            {"snapshot_date": "2026-08-02", "balance": "1000.00"},
            content_type="application/json",
        )

        response = self.client.get(
            reverse("solace-forecast"),
            {"date": "2026-08-03", "months": "1"},
        )
        self.assertEqual(response.status_code, 200)
        forecast = response.json()
        self.assertEqual(forecast["forecast_start"], "2026-08-03")
        self.assertEqual(forecast["through"], "2026-09-03")
        self.assertEqual(forecast["total_bills"], "650.00")
        self.assertEqual(forecast["total_contributions"], "400.00")
        self.assertEqual(forecast["lowest_balance"], "400.00")
        self.assertEqual(forecast["lowest_balance_date"], "2026-08-10")
        self.assertEqual(forecast["bills_only_surplus"], "400.00")
        self.assertEqual(forecast["safe_to_withdraw"], "300.00")
        self.assertEqual(forecast["ending_balance"], "750.00")
        self.assertTrue(forecast["is_covered"])
        self.assertEqual(
            [row["date"] for row in forecast["timeline"]],
            ["2026-08-10", "2026-08-15", "2026-08-20", "2026-08-29"],
        )

    def test_balance_forecast_reports_required_opening_without_snapshot(self):
        create_bill(
            self.admin,
            name="Insurance",
            amount="450.00",
            due_at=timezone.make_aware(datetime(2026, 8, 10, 9)),
        )
        forecast = self.client.get(
            reverse("solace-forecast"),
            {"date": "2026-08-03", "months": "1"},
        ).json()
        self.assertIsNone(forecast["opening_balance"])
        self.assertIsNone(forecast["safe_to_withdraw"])
        self.assertIsNone(forecast["is_covered"])
        self.assertEqual(forecast["required_opening_balance"], "450.00")

    def test_balance_forecast_validates_horizon(self):
        response = self.client.get(reverse("solace-forecast"), {"months": "25"})
        self.assertEqual(response.status_code, 400)

    def test_purchase_quick_saving_caps_at_target_and_rejects_closed_goal(self):
        purchase = create_purchase(
            self.admin,
            name="Sofa",
            target_amount="500.00",
            saved_amount="450.00",
        )
        url = reverse("solace-purchase-add-saved", args=[purchase.id])
        response = self.client.post(
            url,
            {"amount": "100.00"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["saved_amount"], "500.00")
        self.assertEqual(response.json()["remaining_amount"], "0.00")

        response = self.client.post(
            url,
            {"amount": "0.00"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        purchase.status = PlannedPurchase.Status.BOUGHT
        purchase.save(update_fields=["status", "updated_at"])
        response = self.client.post(
            url,
            {"amount": "1.00"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_generated_checklist_item_can_be_hidden_and_restored(self):
        create_payday(
            self.admin,
            title="Pay",
            expected_amount="1000.00",
            pay_at=timezone.make_aware(datetime(2026, 8, 1, 9)),
            recurrence_rule="FREQ=WEEKLY;INTERVAL=2",
        )
        bucket = create_bucket(
            self.admin,
            name="Bills",
            allocation_method=BudgetBucket.AllocationMethod.PERCENTAGE,
            allocation_value="50.00",
        )
        self.client.post(f"{reverse('solace-plan-checklist')}?date=2026-08-03")
        source_key = f"pay-plan:bucket:{bucket.id}"
        response = self.client.post(
            reverse("solace-checklist-preferences"),
            {"source_key": source_key, "label": "Transfer to Bills", "is_hidden": True},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(PaydayChecklistPreference.objects.get().is_hidden)
        visible = self.client.get(reverse("solace-checklist-list")).json()
        self.assertEqual(len(visible), 3)
        self.assertNotIn("Transfer to Bills", [row["title"] for row in visible])
        self.client.post(
            reverse("solace-checklist-preferences"),
            {"source_key": source_key, "label": "Transfer to Bills", "is_hidden": False},
            content_type="application/json",
        )
        self.assertEqual(len(self.client.get(reverse("solace-checklist-list")).json()), 4)

    def test_health_and_category_report_return_actionable_data(self):
        create_bill(
            self.admin,
            name="Power",
            category="utilities",
            amount="120.00",
            due_at=timezone.now() + timedelta(days=3),
            recurrence_rule="FREQ=MONTHLY",
        )
        create_bill(
            self.admin,
            name="Excluded",
            category="utilities",
            amount="20.00",
            due_at=timezone.now() + timedelta(days=4),
            recurrence_rule="FREQ=MONTHLY",
            include_in_set_aside=False,
        )
        create_bill(
            self.admin,
            name="Old",
            category="utilities",
            amount="10.00",
            due_at=timezone.now() + timedelta(days=5),
            recurrence_rule="FREQ=MONTHLY",
            is_active=False,
        )
        health = self.client.get(reverse("solace-health")).json()
        self.assertEqual(health["status"], "error")
        self.assertIn("no_income", [row["code"] for row in health["issues"]])
        report = self.client.get(reverse("solace-category-report")).json()
        self.assertEqual(report["categories"][0]["category"], "utilities")
        self.assertEqual(report["categories"][0]["annual_total"], "1680.00")
        self.assertEqual(report["categories"][0]["weekly_total"], "32.31")
        self.assertEqual(report["categories"][0]["monthly_total"], "140.00")
        self.assertEqual(report["bill_count"], 2)

        included = self.client.get(
            reverse("solace-category-report"),
            {"included": "1"},
        ).json()
        self.assertEqual(included["annual_total"], "1440.00")
        all_bills = self.client.get(
            reverse("solace-category-report"),
            {"active": "0"},
        ).json()
        self.assertEqual(all_bills["annual_total"], "1800.00")

    def test_bootstrap_loads_the_complete_workspace(self):
        response = self.client.get(reverse("solace-bootstrap"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {
                "bills", "paydays", "purchases", "buckets", "subscriptions",
                "checklist", "plan", "settings", "categories", "balances",
                "health", "category_report", "closeout", "forecast",
                "checklist_preferences",
            },
            set(response.json()),
        )

    def test_readable_exports_include_csv_and_xlsx(self):
        create_bill(self.admin, name="Internet", amount="89.00", due_at=_future())
        response = self.client.get(
            reverse("solace-csv-export", kwargs={"export_type": "bills"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Internet", response.content.decode("utf-8-sig"))
        self.assertIn("solace-bills.csv", response["Content-Disposition"])

        response = self.client.get(reverse("solace-xlsx-export"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"PK"))
        self.assertIn("solace-readable-backup.xlsx", response["Content-Disposition"])

    def test_bill_csv_import_is_previewed_before_confirmation(self):
        upload = SimpleUploadedFile(
            "bills.csv",
            (
                b"name,amount,frequency,due_day,start_date,category,active\n"
                b"Internet,89.50,Monthly,12,2026-01-01,Utilities,yes\n"
                b"Broken,0,Monthly,1,2026-01-01,Other,yes\n"
            ),
            content_type="text/csv",
        )
        preview = self.client.post(
            reverse("solace-bill-import-preview"),
            {"file": upload},
        )
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.json()["row_count"], 2)
        self.assertEqual(preview.json()["ready_count"], 1)
        self.assertEqual(preview.json()["error_count"], 1)
        self.assertFalse(Bill.objects.filter(name="Internet").exists())

        confirmed = self.client.post(reverse("solace-bill-import-confirm"))
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.json(), {"imported_count": 1, "skipped_count": 1})
        bill = Bill.objects.get(name="Internet")
        self.assertEqual(bill.amount, Decimal("89.50"))
        self.assertEqual(bill.recurrence_rule, "FREQ=MONTHLY")
        self.assertTrue(bill.occurrences.exists())

    def test_due_reminders_are_generic_and_idempotent(self):
        self.client.get(reverse("solace-settings"))
        create_bill(
            self.admin,
            name="Secret mortgage",
            amount="9999.00",
            due_at=timezone.now() + timedelta(days=1),
        )
        self.assertEqual(send_due_reminders(), 1)
        self.assertEqual(send_due_reminders(), 0)
        reminder = Notification.objects.get(source_node="solace")
        self.assertNotIn("mortgage", reminder.message.lower())
        self.assertNotIn("9999", reminder.message)
        self.assertEqual(reminder.action_url.split("&")[0], "/solace?tab=schedule")


class SolaceSearchHubAuditTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)

    def test_search_requires_reauth_and_audits_access(self):
        _login(self.client, "admin")
        create_bill(self.admin, name="Insurance", provider="Home Co")
        resp = self.client.get(reverse("solace-search"), {"q": "Insurance"})
        self.assertEqual(resp.status_code, 403)
        _reauth(self.client)
        resp = self.client.get(reverse("solace-search"), {"q": "Insurance"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["bills"][0]["name"], "Insurance")
        self.assertTrue(AuditLog.objects.filter(action="sensitive_node_accessed").exists())

    def test_hub_solace_content_needs_sensitive_unlock(self):
        create_bill(self.admin, name="Mortgage", due_at=_future())
        locked = get_hub_widgets(self.admin, sensitive_unlocked=False)
        unlocked = get_hub_widgets(self.admin, sensitive_unlocked=True)
        locked_items = [w for w in locked if w["key"] == "solace_bills_due"]
        unlocked_items = [w for w in unlocked if w["key"] == "solace_bills_due"]
        if locked_items and unlocked_items:
            self.assertEqual(locked_items[0]["items"], [])
            self.assertEqual(unlocked_items[0]["items"][0]["name"], "Mortgage")

    def test_calendar_hides_financial_until_reauth(self):
        _login(self.client, "admin")
        bill = create_bill(self.admin, name="Council rates", due_at=_future())
        resp = self.client.get(reverse("calendar-event-list"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])
        resp = self.client.get(reverse("calendar-event-detail", args=[bill.calendar_event_id]))
        self.assertEqual(resp.status_code, 403)
        _reauth(self.client)
        resp = self.client.get(reverse("calendar-event-list"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Council rates", resp.json()[0]["title"])
        resp = self.client.get(reverse("calendar-event-detail", args=[bill.calendar_event_id]))
        self.assertEqual(resp.status_code, 200)


def _make_legacy_solace_db() -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    try:
        conn.executescript(
            """
            create table category (id integer primary key, name text, category_type text, active boolean);
            create table recurring_bill (
                id integer primary key, name text, amount real, frequency text, due_day integer,
                due_month integer, start_date text, end_date text, category_id integer, active boolean,
                autopay boolean, account_name text, include_in_set_aside boolean, notes text
            );
            create table bill_occurrence (
                id integer primary key, recurring_bill_id integer, due_date text, amount real,
                status text, paid_date text, notes text
            );
            create table planned_purchase (
                id integer primary key, name text, target_amount real, amount_saved real,
                target_date text, category_id integer, priority text, status text, notes text
            );
            create table bucket (
                id integer primary key, name text, percentage real, fixed_amount real,
                rounding_increment integer, cap_to_remaining boolean, bucket_type text,
                active boolean, sort_order integer, notes text
            );
            create table income_source (
                id integer primary key, owner_name text, name text, amount real,
                frequency text, next_pay_date text, active boolean, notes text
            );
            create table payday_checklist_item (
                id integer primary key, cycle_start text, item_key text, label text,
                amount real, completed boolean, completed_at text, sort_order integer
            );
            create table settings (
                id integer primary key, budget_year integer, default_buffer_amount real,
                currency_symbol text, show_help_tips boolean, payday_bill_handling text,
                first_payday text
            );
            create table account_balance_snapshot (
                id integer primary key, snapshot_date text, balance real, notes text
            );
            create table payday_checklist_preference (
                id integer primary key, item_key text, label text, hidden boolean, reason text
            );
            create table cycle_closeout (
                id integer primary key, cycle_start text, cycle_end text,
                status text, closed_at text, notes text
            );
            """
        )
        conn.executemany(
            "insert into category values (?, ?, ?, ?)",
            [(1, "Utilities", "Bill", 1), (2, "Subscriptions", "Bill", 1), (3, "Travel", "Purchase", 1)],
        )
        conn.executemany(
            "insert into recurring_bill values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (1, "Electricity", 120.5, "Monthly", 12, None, "2026-01-01", "2027-12-12", 1, 1, 0, "Power Co", 1, ""),
                (2, "Streaming", 14.99, "Monthly", 15, None, "2026-01-01", None, 2, 1, 1, "Stream Co", 1, "Family plan"),
                (3, "Old bill", 99.0, "Monthly", 1, None, "2026-01-01", None, 1, 0, 0, "", 1, ""),
            ],
        )
        conn.execute(
            "insert into settings values (?, ?, ?, ?, ?, ?, ?)",
            (1, 2026, 250.0, "A$", 0, "previous_cycle", "2026-08-01"),
        )
        conn.execute(
            "insert into account_balance_snapshot values (?, ?, ?, ?)",
            (1, "2026-08-02", 3100.0, "Imported balance"),
        )
        conn.execute(
            "insert into payday_checklist_preference values (?, ?, ?, ?, ?)",
            (1, "auto-transfer", "Automatic transfer", 1, "Handled by bank"),
        )
        conn.execute(
            "insert into cycle_closeout values (?, ?, ?, ?, ?, ?)",
            (1, "2026-07-18", "2026-07-31", "Closed", "2026-08-01T08:00:00", "Done"),
        )
        conn.executemany(
            "insert into bill_occurrence values (?, ?, ?, ?, ?, ?, ?)",
            [
                (1, 1, "2026-08-12", 120.5, "Upcoming", None, ""),
                (2, 2, "2026-08-15", 14.99, "Upcoming", None, ""),
            ],
        )
        conn.execute(
            "insert into planned_purchase values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (1, "Holiday", 2000.0, 300.0, "2026-12-12", 3, "High", "Active", "Flights"),
        )
        conn.execute(
            "insert into bucket values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (1, "Bills", 25.0, None, 10, 0, "Bills", 1, 10, ""),
        )
        conn.execute(
            "insert into income_source values (?, ?, ?, ?, ?, ?, ?, ?)",
            (1, "Alex", "Pay", 2500.0, "Fortnightly", "2026-08-01", 1, ""),
        )
        conn.executemany(
            "insert into payday_checklist_item values (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (1, "2026-07-01", "old", "Old cycle item", 1.0, 0, None, 10),
                (2, "2026-08-01", "new", "Transfer to Bills", 500.0, 1, "2026-08-01T10:00:00", 20),
            ],
        )
        conn.commit()
    finally:
        conn.close()
    return tmp.name


class SolaceImportTests(TestCase):
    def test_import_solace_dry_run_rolls_back(self):
        db_path = _make_legacy_solace_db()
        out = io.StringIO()
        call_command("import_solace", "--sqlite-db", db_path, "--dry-run", stdout=out)
        self.assertIn("DRY-RUN", out.getvalue())
        self.assertEqual(Bill.objects.count(), 0)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_import_solace_applies_and_is_idempotent(self):
        db_path = _make_legacy_solace_db()
        out = io.StringIO()
        call_command("import_solace", "--sqlite-db", db_path, stdout=out)
        self.assertEqual(Bill.objects.count(), 2)
        self.assertEqual(Subscription.objects.count(), 0)
        self.assertEqual(Payday.objects.count(), 1)
        self.assertEqual(PlannedPurchase.objects.count(), 1)
        self.assertEqual(BudgetBucket.objects.count(), 1)
        self.assertEqual(PaydayChecklistItem.objects.count(), 1)
        self.assertEqual(AccountBalanceSnapshot.objects.count(), 1)
        self.assertEqual(PaydayChecklistPreference.objects.count(), 1)
        self.assertEqual(CycleCloseout.objects.count(), 1)
        self.assertEqual(SolaceSettings.objects.get().currency_symbol, "A$")
        self.assertEqual(SolaceSettings.objects.get().payday_bill_handling, "previous_cycle")
        self.assertEqual(SolaceSettings.objects.get().cycle_anchor_date, date(2026, 8, 1))
        self.assertEqual(Bill.objects.get(name="Electricity").category, "utilities")
        self.assertEqual(Bill.objects.get(name="Electricity").end_date, date(2027, 12, 12))
        self.assertEqual(Bill.objects.get(name="Streaming").category, "subscription")
        self.assertTrue(Bill.objects.get(name="Streaming").is_autopay)
        self.assertEqual(PaydayChecklistItem.objects.get().title, "Transfer to Bills")
        self.assertEqual(BudgetBucket.objects.get().allocation_method, "percentage")
        self.assertEqual(BudgetBucket.objects.get().allocation_value, 25)
        self.assertEqual(BudgetBucket.objects.get().rounding_increment, 10)
        self.assertEqual(PaydayChecklistItem.objects.get().cycle_start.isoformat(), "2026-08-01")
        imported_occurrence = BillOccurrence.objects.get(
            bill__name="Electricity",
            due_at__date=date(2026, 8, 12),
        )
        self.assertEqual(imported_occurrence.amount, 120.5)
        occurrence_count = BillOccurrence.objects.count()

        out = io.StringIO()
        call_command("import_solace", "--sqlite-db", db_path, stdout=out)
        self.assertIn("bills: 0", out.getvalue())
        self.assertEqual(Bill.objects.count(), 2)
        self.assertEqual(Subscription.objects.count(), 0)
        self.assertEqual(BillOccurrence.objects.count(), occurrence_count)

        streaming = Bill.objects.get(name="Streaming")
        streaming.is_autopay = False
        streaming.save(update_fields=["is_autopay", "updated_at"])
        out = io.StringIO()
        call_command("import_solace", "--sqlite-db", db_path, stdout=out)
        streaming.refresh_from_db()
        self.assertTrue(streaming.is_autopay)
        self.assertIn("bills_enriched: 1", out.getvalue())

    def test_import_solace_verify_reports_parity_and_actionable_drift(self):
        db_path = _make_legacy_solace_db()
        call_command("import_solace", "--sqlite-db", db_path, stdout=io.StringIO())

        out = io.StringIO()
        call_command("import_solace", "--sqlite-db", db_path, "--verify", stdout=out)
        self.assertIn("Verification passed", out.getvalue())

        bill = Bill.objects.get(name="Electricity")
        bill.amount = Decimal("999.00")
        bill.save(update_fields=["amount", "updated_at"])

        with self.assertRaisesMessage(
            CommandError,
            "bill Electricity: amount expected Decimal('120.50'), found Decimal('999.00')",
        ):
            call_command(
                "import_solace",
                "--sqlite-db",
                db_path,
                "--verify",
                stdout=io.StringIO(),
            )
