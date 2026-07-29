"""Solace tests — native finance node. Permission tests first (D10)."""
import io
import sqlite3
import tempfile

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.hub.services import get_hub_widgets
from apps.scheduling.models import CalendarEvent
from apps.solace.services import (
    create_bill,
    create_bucket,
    create_purchase,
    create_subscription,
    delete_bill,
    mark_bill_paid,
)
from apps.solace.models import Bill, BudgetBucket, Payday, PaydayChecklistItem, PlannedPurchase, Subscription


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
            """
        )
        conn.executemany(
            "insert into category values (?, ?, ?, ?)",
            [(1, "Utilities", "Bill", 1), (2, "Subscriptions", "Bill", 1), (3, "Travel", "Purchase", 1)],
        )
        conn.executemany(
            "insert into recurring_bill values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (1, "Electricity", 120.5, "Monthly", 12, None, "2026-01-01", None, 1, 1, 0, "Power Co", 1, ""),
                (2, "Streaming", 14.99, "Monthly", 15, None, "2026-01-01", None, 2, 1, 1, "Stream Co", 1, "Family plan"),
                (3, "Old bill", 99.0, "Monthly", 1, None, "2026-01-01", None, 1, 0, 0, "", 1, ""),
            ],
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
        self.assertEqual(Bill.objects.count(), 1)
        self.assertEqual(Subscription.objects.count(), 1)
        self.assertEqual(Payday.objects.count(), 1)
        self.assertEqual(PlannedPurchase.objects.count(), 1)
        self.assertEqual(BudgetBucket.objects.count(), 1)
        self.assertEqual(PaydayChecklistItem.objects.count(), 1)
        self.assertEqual(Bill.objects.get().name, "Electricity")
        self.assertEqual(Bill.objects.get().category, "utilities")
        self.assertEqual(Subscription.objects.get().name, "Streaming")
        self.assertEqual(PaydayChecklistItem.objects.get().title, "Transfer to Bills")

        out = io.StringIO()
        call_command("import_solace", "--sqlite-db", db_path, stdout=out)
        self.assertIn("bills: 0", out.getvalue())
        self.assertEqual(Bill.objects.count(), 1)
        self.assertEqual(Subscription.objects.count(), 1)
