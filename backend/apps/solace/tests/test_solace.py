"""Solace tests — native finance node. Permission tests first (D10)."""
import io
import sqlite3
import tempfile
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

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

    def test_linked_bill_is_edited_and_deleted_in_solace_and_refreshes_homestead(self):
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
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(str(Bill.objects.get(pk=bill_id).amount), "1.00")
        self.assertEqual(
            str(InsurancePolicy.objects.get(solace_bill_ref=bill_id).premium_amount),
            "1.00",
        )
        removed = self.client.delete(url)
        self.assertEqual(removed.status_code, 204)
        self.assertFalse(Bill.objects.filter(pk=bill_id).exists())
        self.assertFalse(InsurancePolicy.objects.filter(solace_bill_ref=bill_id).exists())

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

    def test_subscription_category_bill_creates_financial_event(self):
        subscription = create_bill(
            self.admin,
            name="Streaming",
            category="subscription",
            amount="12.99",
            due_at=_future(),
            recurrence_rule="FREQ=MONTHLY",
        )
        event = CalendarEvent.objects.get(pk=subscription.calendar_event_id)
        self.assertEqual(event.source_node.key, "solace")
        self.assertEqual(event.sensitivity, "financial")

    def test_subscription_category_uses_bill_payment_history_and_autopay(self):
        response = self.client.post(
            reverse("solace-bill-list"),
            {
                "name": "Music",
                "category": "subscription",
                "amount": "14.99",
                "due_at": _future().isoformat(),
                "recurrence_rule": "FREQ=MONTHLY",
                "is_autopay": True,
                "include_in_set_aside": True,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.json())
        self.assertTrue(response.json()["is_autopay"])
        occurrence_id = response.json()["next_occurrence_id"]

        paid = self.client.post(
            reverse("solace-occurrence-action", args=[occurrence_id, "paid"]),
            {},
            content_type="application/json",
        )
        self.assertEqual(paid.status_code, 200, paid.json())
        self.assertEqual(paid.json()["status"], BillOccurrence.Status.PAID)
        timeline = self.client.get(
            reverse("solace-bill-occurrences", args=[response.json()["id"]])
        ).json()
        timeline_rows = timeline["upcoming"] + timeline["history"]
        recorded = next(row for row in timeline_rows if row["id"] == occurrence_id)
        self.assertEqual(recorded["status"], BillOccurrence.Status.PAID)

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

    def test_occurrence_on_local_first_day_of_next_cycle_is_not_in_current_cycle(self):
        from apps.solace.selectors import list_bill_occurrences

        brisbane = ZoneInfo("Australia/Brisbane")
        self.admin.household.timezone = "Australia/Brisbane"
        self.admin.household.save(update_fields=["timezone"])
        with timezone.override(brisbane):
            bill = create_bill(
                self.admin,
                name="Next cycle electricity",
                amount="60.00",
                due_at=datetime(2026, 8, 12, 0, 0, tzinfo=brisbane),
            )
            current = list_bill_occurrences(
                self.admin,
                start=date(2026, 7, 29),
                end=date(2026, 8, 11),
            )
            next_cycle = list_bill_occurrences(
                self.admin,
                start=date(2026, 8, 12),
                end=date(2026, 8, 25),
            )

        self.assertNotIn(bill.id, [row.bill_id for row in current])
        self.assertIn(bill.id, [row.bill_id for row in next_cycle])

    def test_occurrence_generation_uses_household_timezone_not_djangos_active_one(self):
        """A bill due at household-local midnight must generate as due "today", even though
        Django's active timezone is never activated per-request in production (it stays UTC
        inside Docker). Unlike the sibling test above, this one deliberately leaves Django's
        active timezone at UTC instead of overriding it, reproducing the real deployment: a
        household-local "due today" bill was silently excluded because occurrence generation
        compared it against a window boundary mislabelled as UTC instead of as household-local
        (owner report, 2026-08-12 — utility bills due today missing from Money → Now)."""
        brisbane = ZoneInfo("Australia/Brisbane")
        self.admin.household.timezone = "Australia/Brisbane"
        self.admin.household.save(update_fields=["timezone"])
        self.assertEqual(str(timezone.get_current_timezone()), "UTC")
        bill = create_bill(
            self.admin,
            name="Electricity",
            amount="60.00",
            due_at=datetime(2026, 8, 12, 0, 0, tzinfo=brisbane),
        )
        values = occurrence_datetimes(bill, date(2026, 8, 12), date(2026, 8, 12))
        self.assertEqual(len(values), 1)

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
        # Entering a backdated bill settles its history, so put one month back to unpaid to
        # stand for a payment that really was missed — that is what "all_unpaid" acts on.
        unpaid.status = BillOccurrence.Status.UPCOMING
        unpaid.paid_at = None
        unpaid.save(update_fields=["status", "paid_at"])
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

    def test_moving_first_due_forward_removes_the_obsolete_overdue_occurrence(self):
        old_due = timezone.now() - timedelta(days=7)
        new_due = timezone.now() + timedelta(days=10)
        bill = create_bill(
            self.admin,
            name="Corrected start date",
            amount="70.00",
            due_at=old_due,
        )
        old_occurrence = BillOccurrence.objects.get(bill=bill, due_at=old_due)
        # Backdated bills are settled on entry; recreate the reported stale-overdue state.
        old_occurrence.status = BillOccurrence.Status.UPCOMING
        old_occurrence.paid_at = None
        old_occurrence.save(update_fields=["status", "paid_at"])

        response = self.client.patch(
            reverse("solace-bill-detail", args=[bill.id]),
            {"due_at": new_due.isoformat(), "occurrence_update_scope": "future_unpaid"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200, response.json())
        self.assertFalse(BillOccurrence.objects.filter(pk=old_occurrence.pk).exists())
        replacement = BillOccurrence.objects.get(bill=bill)
        self.assertEqual(replacement.due_at, new_due)
        self.assertFalse(response.json()["is_overdue"])
        self.assertEqual(self.client.get(reverse("solace-now")).json()["overdue_count"], 0)

    def test_schedule_correction_preserves_skipped_history(self):
        old_due = timezone.now() + timedelta(days=1)
        bill = create_bill(
            self.admin,
            name="Rescheduled weekly bill",
            amount="30.00",
            due_at=old_due,
            recurrence_rule="FREQ=WEEKLY",
        )
        skipped = bill.occurrences.first()
        self.client.post(reverse("solace-occurrence-action", args=[skipped.id, "skip"]))

        response = self.client.patch(
            reverse("solace-bill-detail", args=[bill.id]),
            {"due_at": (old_due + timedelta(days=2)).isoformat()},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200, response.json())
        skipped.refresh_from_db()
        self.assertEqual(skipped.status, BillOccurrence.Status.SKIPPED)
        self.assertTrue(
            BillOccurrence.objects.filter(bill=bill, status=BillOccurrence.Status.UPCOMING).exists()
        )

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
            purpose=BudgetBucket.Purpose.BILLS,
            allocation_method=BudgetBucket.AllocationMethod.PERCENTAGE,
            allocation_value="25.00",
            rounding_increment="10.00",
            position=10,
        )
        self.savings = create_bucket(
            self.admin,
            name="Savings",
            purpose=BudgetBucket.Purpose.SAVINGS,
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
        rent = create_bill(
            self.admin,
            name="Rent",
            amount="800.00",
            due_at=timezone.make_aware(datetime(2026, 8, 3, 9)),
            recurrence_rule="FREQ=MONTHLY",
        )
        # This scenario is a bill that is due and not yet paid. Entering a bill settles any
        # occurrence already past, so reopen the one the closeout is meant to act on.
        rent.occurrences.filter(due_at__date=date(2026, 8, 3)).update(
            status=BillOccurrence.Status.UPCOMING, paid_at=None
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
            purpose=BudgetBucket.Purpose.BILLS,
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
        create_bill(
            self.admin,
            name="Streaming",
            category="subscription",
            amount="50.00",
            due_at=timezone.make_aware(datetime(2026, 8, 20, 9)),
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

    def test_balance_forecast_counts_pay_into_a_bucket_marked_bills_by_purpose(self):
        """A bucket created through the UI sets `purpose`, never the old free-text category.

        The forecast used to decide "is this the bills bucket?" by looking for the substring
        "bill" in that free-text field, which the bucket form does not populate — so every
        household's projected income silently came out as zero while their bills still counted.
        """
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
            purpose=BudgetBucket.Purpose.BILLS,
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

        forecast = self.client.get(
            reverse("solace-forecast"),
            {"date": "2026-08-03", "months": "1"},
        ).json()

        self.assertEqual(forecast["total_contributions"], "400.00")
        self.assertGreater(
            len([row for row in forecast["timeline"] if row["contributions"] != "0.00"]), 0
        )

    def test_balance_forecast_ignores_a_bucket_that_is_not_for_bills(self):
        create_payday(
            self.admin,
            title="Household pay",
            expected_amount="1000.00",
            pay_at=timezone.make_aware(datetime(2026, 8, 15, 9)),
            recurrence_rule="FREQ=WEEKLY;INTERVAL=2",
        )
        create_bucket(
            self.admin,
            name="Holiday fund",
            purpose=BudgetBucket.Purpose.SAVINGS,
            allocation_method=BudgetBucket.AllocationMethod.PERCENTAGE,
            allocation_value="20.00",
            rounding_increment="1.00",
        )
        forecast = self.client.get(
            reverse("solace-forecast"),
            {"date": "2026-08-03", "months": "1"},
        ).json()
        self.assertEqual(forecast["total_contributions"], "0.00")

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
                "bills", "paydays", "purchases", "buckets",
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

    def test_import_solace_applies_and_is_idempotent(self):
        db_path = _make_legacy_solace_db()
        out = io.StringIO()
        call_command("import_solace", "--sqlite-db", db_path, stdout=out)
        self.assertEqual(Bill.objects.count(), 2)
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


class BucketEntryTests(TestCase):
    """A bucket balance is a running total with history, not a number you overwrite."""

    def setUp(self):
        self.admin = _make_user("bucketkeeper", User.Role.ADMIN)
        _login(self.client, "bucketkeeper")
        _reauth(self.client)
        self.bucket = create_bucket(
            self.admin, name="Car fund", target_amount="2000.00", current_amount="500.00",
        )

    def _entry(self, **payload):
        return self.client.post(
            reverse("solace-bucket-entry-list", args=[self.bucket.id]),
            payload, content_type="application/json",
        )

    def test_money_in_raises_the_balance_and_records_it(self):
        response = self._entry(kind="deposit", amount="150.00", note="Payday transfer")
        self.assertEqual(response.status_code, 201, response.json())
        self.assertEqual(response.json()["balance_after"], "650.00")
        self.bucket.refresh_from_db()
        self.assertEqual(self.bucket.current_amount, Decimal("650.00"))

    def test_money_out_lowers_the_balance(self):
        self._entry(kind="withdrawal", amount="200.00", note="New tyres")
        self.bucket.refresh_from_db()
        self.assertEqual(self.bucket.current_amount, Decimal("300.00"))

    def test_history_is_returned_newest_first_with_running_balances(self):
        self._entry(kind="deposit", amount="100.00")
        self._entry(kind="withdrawal", amount="50.00")
        rows = self.client.get(reverse("solace-bucket-entry-list", args=[self.bucket.id])).json()
        self.assertEqual([row["balance_after"] for row in rows], ["550.00", "600.00"])

    def test_deleting_an_entry_takes_its_effect_back_out(self):
        entry = self._entry(kind="deposit", amount="100.00").json()
        self.client.delete(
            reverse("solace-bucket-entry-detail", args=[self.bucket.id, entry["id"]])
        )
        self.bucket.refresh_from_db()
        self.assertEqual(self.bucket.current_amount, Decimal("500.00"))

    def test_a_zero_or_negative_amount_is_rejected(self):
        self.assertEqual(self._entry(kind="deposit", amount="0").status_code, 400)
        self.assertEqual(self._entry(kind="deposit", amount="-5.00").status_code, 400)

    def test_correcting_the_balance_by_hand_still_leaves_a_trace(self):
        self.client.patch(
            reverse("solace-bucket-detail", args=[self.bucket.id]),
            {"current_amount": "800.00"}, content_type="application/json",
        )
        rows = self.client.get(reverse("solace-bucket-entry-list", args=[self.bucket.id])).json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["kind"], "adjustment")
        self.assertEqual(rows[0]["amount"], "300.00")
        self.assertEqual(rows[0]["balance_after"], "800.00")

    def test_child_accounts_cannot_move_bucket_money(self):
        _make_user("bucketchild", User.Role.USER, is_child=True)
        _login(self.client, "bucketchild")
        self.assertEqual(self._entry(kind="deposit", amount="10.00").status_code, 403)


class BucketAllocationLimitTests(TestCase):
    """Active percentage buckets describe shares of one pay and cannot exceed the whole."""

    def setUp(self):
        self.admin = _make_user("bucketallocator", User.Role.ADMIN)
        _login(self.client, "bucketallocator")
        _reauth(self.client)
        self.first = create_bucket(
            self.admin,
            name="Bills",
            allocation_method="percentage",
            allocation_value="60.00",
        )

    def test_creating_a_bucket_cannot_take_the_total_over_100_percent(self):
        response = self.client.post(
            reverse("solace-bucket-list"),
            {
                "name": "Savings",
                "allocation_method": "percentage",
                "allocation_value": "40.01",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400, response.json())
        self.assertIn("100%", str(response.json()))
        self.assertFalse(BudgetBucket.objects.filter(name="Savings").exists())

    def test_updating_a_bucket_cannot_take_the_total_over_100_percent(self):
        second = create_bucket(
            self.admin,
            name="Savings",
            allocation_method="percentage",
            allocation_value="40.00",
        )
        response = self.client.patch(
            reverse("solace-bucket-detail", args=[second.id]),
            {"allocation_value": "40.01"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400, response.json())
        second.refresh_from_db()
        self.assertEqual(second.allocation_value, Decimal("40.00"))

    def test_inactive_percentage_buckets_do_not_consume_the_limit(self):
        response = self.client.post(
            reverse("solace-bucket-list"),
            {
                "name": "Future plan",
                "allocation_method": "percentage",
                "allocation_value": "100.00",
                "is_active": False,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.json())


class SolaceNowTests(TestCase):
    """The landing answer: what is owed before the next payday, with its running total."""

    def setUp(self):
        self.admin = _make_user("nowuser", User.Role.ADMIN)
        _login(self.client, "nowuser")
        _reauth(self.client)
        create_payday(
            self.admin, title="Pay", expected_amount="2000.00",
            pay_at=timezone.now() - timedelta(days=2),
            recurrence_rule="FREQ=WEEKLY;INTERVAL=2",
        )

    def _now(self):
        response = self.client.get(reverse("solace-now"))
        self.assertEqual(response.status_code, 200, response.json())
        return response.json()

    def test_an_unpaid_bill_due_this_cycle_is_listed_with_its_total(self):
        create_bill(
            self.admin, name="Electricity", amount="120.50",
            due_at=timezone.now() + timedelta(days=3),
        )
        data = self._now()
        self.assertEqual([row["bill_name"] for row in data["due"]], ["Electricity"])
        self.assertEqual(data["due_total"], "120.50")

    def test_bill_due_on_next_payday_is_not_in_cycle_ending_day_before(self):
        brisbane = ZoneInfo("Australia/Brisbane")
        self.admin.household.timezone = "Australia/Brisbane"
        self.admin.household.save(update_fields=["timezone"])
        with timezone.override(brisbane):
            Payday.objects.all().delete()
            create_payday(
                self.admin,
                title="Pay",
                expected_amount="2000.00",
                pay_at=timezone.make_aware(datetime(2026, 8, 12, 9), brisbane),
                recurrence_rule="FREQ=WEEKLY;INTERVAL=2",
            )
            settings = self.client.get(reverse("solace-settings"))
            self.assertEqual(settings.status_code, 200)
            self.client.patch(
                reverse("solace-settings"),
                {"payday_bill_handling": "previous_cycle"},
                content_type="application/json",
            )
            create_bill(
                self.admin,
                name="Electricity",
                amount="60.00",
                due_at=timezone.make_aware(datetime(2026, 8, 12, 0), brisbane),
            )

            response = self.client.get(reverse("solace-now"), {"date": "2026-08-11"})
            self.assertEqual(response.status_code, 200, response.json())
            data = response.json()
            self.assertEqual(data["cycle_start"], "2026-07-29")
            self.assertEqual(data["cycle_end"], "2026-08-11")
            self.assertNotIn("Electricity", [row["bill_name"] for row in data["due"]])

    def test_an_overdue_bill_is_still_owed_and_is_counted_separately(self):
        # A bill entered with a past due date is settled as paid on entry by design, so the way
        # an occurrence becomes genuinely overdue is time passing without it being marked off.
        create_bill(
            self.admin, name="Water", amount="80.00",
            due_at=timezone.now() + timedelta(days=3),
        )
        bill = Bill.objects.get(name="Water")
        occurrence = BillOccurrence.objects.get(bill__name="Water", status="upcoming")
        overdue_at = timezone.now() - timedelta(days=6)
        # Move both the rule and its generated row to simulate time passing while keeping the
        # occurrence consistent with the schedule it came from.
        bill.due_at = overdue_at
        bill.save(update_fields=["due_at"])
        occurrence.due_at = overdue_at
        occurrence.save(update_fields=["due_at"])
        data = self._now()
        self.assertEqual(data["overdue_count"], 1)
        self.assertEqual(data["overdue_total"], "80.00")
        self.assertIn("Water", [row["bill_name"] for row in data["due"]])

    def test_now_removes_an_obsolete_overdue_row_left_by_an_old_date_edit(self):
        bill = create_bill(
            self.admin,
            name="Corrected water date",
            amount="80.00",
            due_at=timezone.now() + timedelta(days=3),
        )
        stale = BillOccurrence.objects.create(
            household=get_active_household(),
            bill=bill,
            # Deliberately outside Now's normal 90-day lookback: the repair starts from the
            # earliest stored unpaid row so old bad edits are not stranded permanently.
            due_at=timezone.now() - timedelta(days=200),
            amount="80.00",
            created_by=self.admin,
            updated_by=self.admin,
        )

        data = self._now()

        self.assertEqual(data["overdue_count"], 0)
        self.assertFalse(BillOccurrence.objects.filter(pk=stale.pk).exists())
        self.assertIn("Corrected water date", [row["bill_name"] for row in data["due"]])

    def test_marking_one_paid_moves_it_out_of_what_is_owed(self):
        create_bill(
            self.admin, name="Internet", amount="99.00",
            due_at=timezone.now() + timedelta(days=2),
        )
        occurrence_id = self._now()["due"][0]["id"]
        response = self.client.post(
            reverse("solace-occurrence-action", args=[occurrence_id, "paid"]),
            {}, content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.json())
        data = self._now()
        self.assertEqual(data["due"], [])
        self.assertEqual(data["due_total"], "0.00")
        self.assertEqual(data["paid_this_cycle_count"], 1)
        self.assertEqual(data["paid_this_cycle_total"], "99.00")

    def test_bucket_balances_are_summarised(self):
        create_bucket(self.admin, name="Bills", current_amount="400.00")
        create_bucket(self.admin, name="Car", current_amount="250.50")
        self.assertEqual(self._now()["bucket_total"], "650.50")

    def test_the_cycle_window_is_reported(self):
        data = self._now()
        self.assertTrue(data["cycle_start"] < data["cycle_end"])
        self.assertGreaterEqual(data["days_until_cycle_end"], 0)

    def test_children_cannot_read_the_money_landing(self):
        _make_user("nowchild", User.Role.USER, is_child=True)
        _login(self.client, "nowchild")
        self.assertEqual(self.client.get(reverse("solace-now")).status_code, 403)


class SharedIncomeAllocationTests(TestCase):
    """Shared income belongs to the household, not to a person, and can bypass the usual rules.

    Mirrors the standalone app's behaviour: personal percentage splits run on individual income
    only, so a shared deposit cannot inflate someone's contribution.
    """

    def setUp(self):
        self.admin = _make_user("splitter", User.Role.ADMIN)
        _login(self.client, "splitter")
        _reauth(self.client)
        self.bills = create_bucket(
            self.admin, name="Bills", purpose="bills",
            allocation_method="percentage", allocation_value="50.00",
            rounding_increment="0.01", cap_to_remaining=False,
        )
        self.savings = create_bucket(
            self.admin, name="Savings", purpose="savings",
            allocation_method="percentage", allocation_value="10.00",
            rounding_increment="0.01", cap_to_remaining=False,
        )

    def _income(self, **overrides):
        payload = dict(
            title="Pay", expected_amount="1000.00",
            pay_at=timezone.make_aware(datetime(2026, 8, 3, 9)),
            recurrence_rule="FREQ=WEEKLY;INTERVAL=2",
        )
        payload.update(overrides)
        return create_payday(self.admin, **payload)

    def _plan(self):
        from apps.solace.selectors import get_pay_cycle_plan
        return get_pay_cycle_plan(self.admin, as_of=date(2026, 8, 5))

    def test_individual_income_is_grouped_by_owner(self):
        self._income(title="Alex salary", owner_name="Alex")
        self._income(title="Sam salary", owner_name="Sam", expected_amount="500.00")
        people = self._plan()["people"]
        self.assertEqual([row["owner_name"] for row in people], ["Alex", "Sam"])
        self.assertEqual(people[0]["income_total"], "1000.00")
        self.assertEqual(people[1]["income_total"], "500.00")

    def test_shared_income_is_left_out_of_the_personal_breakdown(self):
        self._income(title="Alex salary", owner_name="Alex")
        self._income(title="Rent received", owner_name="Household", income_scope="shared", expected_amount="400.00")
        plan = self._plan()
        self.assertEqual([row["owner_name"] for row in plan["people"]], ["Alex"])
        self.assertEqual(plan["individual_income_total"], "1000.00")
        self.assertEqual(plan["shared_income_total"], "400.00")
        self.assertEqual(plan["income_total"], "1400.00")

    def test_a_lump_share_goes_entirely_to_one_bucket(self):
        self._income(
            title="Tax refund", income_scope="shared", allocation_mode="lump",
            lump_bucket_id=self.savings.id, expected_amount="600.00",
        )
        buckets = {row["bucket_name"]: row["amount"] for row in self._plan()["buckets"]}
        self.assertEqual(buckets["Savings"], "600.00")
        self.assertNotIn("Bills", buckets)

    def test_a_custom_split_applies_percentages_and_gives_the_rest_to_the_remainder(self):
        payday = self._income(
            title="Side income", income_scope="shared", allocation_mode="custom",
            expected_amount="1000.00",
        )
        response = self.client.put(
            reverse("solace-income-allocations", args=[payday.id]),
            [
                {"bucket_id": self.bills.id, "percentage": "70.00", "is_remainder": False},
                {"bucket_id": self.savings.id, "percentage": "0.00", "is_remainder": True},
            ],
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.json())
        buckets = {row["bucket_name"]: row["amount"] for row in self._plan()["buckets"]}
        self.assertEqual(buckets["Bills"], "700.00")
        self.assertEqual(buckets["Savings"], "300.00")

    def test_a_custom_split_without_a_remainder_leaves_the_rest_alone(self):
        payday = self._income(
            title="Side income", income_scope="shared", allocation_mode="custom",
            expected_amount="1000.00",
        )
        self.client.put(
            reverse("solace-income-allocations", args=[payday.id]),
            [{"bucket_id": self.bills.id, "percentage": "40.00", "is_remainder": False}],
            content_type="application/json",
        )
        plan = self._plan()
        buckets = {row["bucket_name"]: row["amount"] for row in plan["buckets"]}
        self.assertEqual(buckets["Bills"], "400.00")
        self.assertEqual(plan["allocated_total"], "400.00")

    def test_only_one_line_may_take_the_remainder(self):
        payday = self._income(title="Side income", income_scope="shared", allocation_mode="custom")
        response = self.client.put(
            reverse("solace-income-allocations", args=[payday.id]),
            [
                {"bucket_id": self.bills.id, "percentage": "0.00", "is_remainder": True},
                {"bucket_id": self.savings.id, "percentage": "0.00", "is_remainder": True},
            ],
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_custom_split_cannot_exceed_100_percent_or_replace_the_saved_split(self):
        payday = self._income(title="Side income", income_scope="shared", allocation_mode="custom")
        url = reverse("solace-income-allocations", args=[payday.id])
        saved = [{"bucket_id": self.bills.id, "percentage": "75.00", "is_remainder": False}]
        self.assertEqual(self.client.put(url, saved, content_type="application/json").status_code, 200)

        response = self.client.put(
            url,
            [
                {"bucket_id": self.bills.id, "percentage": "75.00", "is_remainder": False},
                {"bucket_id": self.savings.id, "percentage": "25.01", "is_remainder": False},
            ],
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400, response.json())
        rows = self.client.get(url).json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["percentage"], "75.00")

    def test_standard_shared_income_still_flows_through_the_usual_rules(self):
        self._income(title="Alex salary", owner_name="Alex")
        self._income(
            title="Board money", income_scope="shared", allocation_mode="standard",
            expected_amount="200.00",
        )
        buckets = {row["bucket_name"]: row["amount"] for row in self._plan()["buckets"]}
        # 50% of each source: 500 from the salary, 100 from the shared income.
        self.assertEqual(buckets["Bills"], "600.00")

    def test_replacing_a_split_removes_the_lines_it_replaces(self):
        payday = self._income(title="Side income", income_scope="shared", allocation_mode="custom")
        url = reverse("solace-income-allocations", args=[payday.id])
        self.client.put(url, [{"bucket_id": self.bills.id, "percentage": "50.00"}], content_type="application/json")
        self.client.put(url, [{"bucket_id": self.savings.id, "percentage": "25.00"}], content_type="application/json")
        rows = self.client.get(url).json()
        self.assertEqual([row["bucket_name"] for row in rows], ["Savings"])


class CycleHistoryTests(TestCase):
    """Closed cycles were being recorded and then never read back."""

    def setUp(self):
        self.admin = _make_user("historian", User.Role.ADMIN)
        _login(self.client, "historian")
        _reauth(self.client)

    def _closeout(self, start: date, status="closed"):
        return CycleCloseout.objects.create(
            household=get_active_household(), created_by=self.admin, updated_by=self.admin,
            cycle_start=start, cycle_end=start + timedelta(days=13), status=status,
            notes=f"Cycle from {start}",
        )

    def test_history_lists_every_cycle_newest_first(self):
        self._closeout(date(2026, 6, 1))
        self._closeout(date(2026, 7, 1))
        rows = self.client.get(reverse("solace-cycle-history")).json()
        self.assertEqual([row["cycle_start"] for row in rows], ["2026-07-01", "2026-06-01"])
        self.assertEqual(rows[0]["notes"], "Cycle from 2026-07-01")

    def test_each_cycle_reports_how_its_bills_went(self):
        bill = create_bill(
            self.admin, name="Power", amount="100.00",
            due_at=timezone.make_aware(datetime(2026, 6, 5, 9)),
        )
        occurrence = BillOccurrence.objects.filter(bill=bill).order_by("due_at").first()
        occurrence.status = BillOccurrence.Status.PAID
        occurrence.save(update_fields=["status"])
        self._closeout(date(2026, 6, 1))
        row = self.client.get(reverse("solace-cycle-history")).json()[0]
        self.assertEqual(row["paid_count"], 1)
        self.assertEqual(row["paid_total"], "100.00")

    def test_children_cannot_read_cycle_history(self):
        _make_user("historychild", User.Role.USER, is_child=True)
        _login(self.client, "historychild")
        self.assertEqual(self.client.get(reverse("solace-cycle-history")).status_code, 403)


class AnnualSummaryTests(TestCase):
    def setUp(self):
        self.admin = _make_user("annualist", User.Role.ADMIN)
        _login(self.client, "annualist")
        _reauth(self.client)

    def _summary(self, year_type="calendar"):
        response = self.client.get(reverse("solace-annual-summary"), {"year_type": year_type})
        self.assertEqual(response.status_code, 200, response.json())
        return response.json()

    def test_bills_group_by_category_ordered_by_cost(self):
        create_bill(
            self.admin, name="Rates", category="council", amount="500.00",
            due_at=timezone.now() + timedelta(days=10), recurrence_rule="",
        )
        create_bill(
            self.admin, name="Internet", category="utilities", amount="80.00",
            due_at=timezone.now() + timedelta(days=12), recurrence_rule="",
        )
        data = self._summary()
        self.assertEqual([row["name"] for row in data["categories"]], ["council", "utilities"])
        self.assertEqual(data["grand_total"], "580.00")

    def test_each_category_breaks_down_by_bill(self):
        create_bill(
            self.admin, name="Water", category="utilities", amount="60.00",
            due_at=timezone.now() + timedelta(days=5), recurrence_rule="",
        )
        create_bill(
            self.admin, name="Internet", category="utilities", amount="90.00",
            due_at=timezone.now() + timedelta(days=6), recurrence_rule="",
        )
        category = self._summary()["categories"][0]
        self.assertEqual([bill["name"] for bill in category["bills"]], ["Internet", "Water"])

    def test_paid_and_outstanding_are_reported_separately(self):
        bill = create_bill(
            self.admin, name="Power", category="utilities", amount="120.00",
            due_at=timezone.now() + timedelta(days=4), recurrence_rule="",
        )
        occurrence = BillOccurrence.objects.get(bill=bill)
        occurrence.status = BillOccurrence.Status.PAID
        occurrence.save(update_fields=["status"])
        data = self._summary()
        self.assertEqual(data["grand_paid"], "120.00")
        self.assertEqual(data["grand_outstanding"], "0.00")

    def test_a_bill_with_no_category_is_still_counted(self):
        create_bill(
            self.admin, name="Odd one", category="", amount="10.00",
            due_at=timezone.now() + timedelta(days=3), recurrence_rule="",
        )
        self.assertEqual(self._summary()["categories"][0]["name"], "Uncategorised")

    def test_the_financial_year_runs_july_to_june(self):
        data = self._summary("financial")
        self.assertTrue(data["period_start"].endswith("-07-01"))
        self.assertTrue(data["period_end"].endswith("-06-30"))
        self.assertTrue(data["period_label"].startswith("FY "))

    def test_an_unknown_year_type_is_rejected(self):
        self.assertEqual(
            self.client.get(reverse("solace-annual-summary"), {"year_type": "lunar"}).status_code,
            400,
        )


class PurchaseCompletionTests(TestCase):
    def setUp(self):
        self.admin = _make_user("shopper", User.Role.ADMIN)
        _login(self.client, "shopper")
        _reauth(self.client)

    def test_marking_a_purchase_bought_shows_it_fully_funded(self):
        purchase = create_purchase(
            self.admin, name="Mower", target_amount="800.00", saved_amount="500.00",
        )
        response = self.client.patch(
            reverse("solace-purchase-detail", args=[purchase.id]),
            {"status": "bought"}, content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(response.json()["saved_amount"], "800.00")

    def test_a_purchase_saved_beyond_its_target_keeps_the_larger_figure(self):
        purchase = create_purchase(
            self.admin, name="Bike", target_amount="400.00", saved_amount="450.00",
        )
        self.client.patch(
            reverse("solace-purchase-detail", args=[purchase.id]),
            {"status": "bought"}, content_type="application/json",
        )
        purchase.refresh_from_db()
        self.assertEqual(purchase.saved_amount, Decimal("450.00"))


class BillReconciliationCachingTests(TestCase):
    """Bootstrap fans out to several sub-views that each need bill occurrences materialised.

    Before this cache, one Money page load reconciled every active bill's occurrences three or
    four times over heavily overlapping windows (owner report, 2026-08-12 — Solace "can take a
    few seconds to load"). This asserts a later, narrower request for the same bill is a no-op.
    """

    def test_a_covered_window_is_not_reconciled_twice(self):
        from apps.solace.views import _ensure_bills_reconciled

        admin = _make_user("reconcileuser", User.Role.ADMIN)
        bill = create_bill(
            admin, name="Electricity", amount="60.00", due_at=timezone.now() + timedelta(days=3),
        )

        class _FakeRequest:
            pass

        request = _FakeRequest()
        with patch(
            "apps.solace.bill_schedule.ensure_bill_occurrences",
        ) as mock_ensure:
            _ensure_bills_reconciled(request, [bill], date(2026, 1, 1), date(2026, 12, 31))
            _ensure_bills_reconciled(request, [bill], date(2026, 3, 1), date(2026, 6, 30))
            mock_ensure.assert_called_once()

    def test_an_uncovered_window_still_reconciles(self):
        from apps.solace.views import _ensure_bills_reconciled

        admin = _make_user("reconcileuser2", User.Role.ADMIN)
        bill = create_bill(
            admin, name="Water", amount="60.00", due_at=timezone.now() + timedelta(days=3),
        )

        class _FakeRequest:
            pass

        request = _FakeRequest()
        with patch(
            "apps.solace.bill_schedule.ensure_bill_occurrences",
        ) as mock_ensure:
            _ensure_bills_reconciled(request, [bill], date(2026, 3, 1), date(2026, 6, 30))
            _ensure_bills_reconciled(request, [bill], date(2026, 1, 1), date(2026, 12, 31))
            self.assertEqual(mock_ensure.call_count, 2)
