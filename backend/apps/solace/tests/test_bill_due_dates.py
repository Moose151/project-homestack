"""Bill due dates must survive the round trip (owner bug report, 2026-08-09).

The reported symptom was that due dates entered on the Bills form never saved. The cause was
in the form, not here: the field was a `datetime-local` input, and a datetime input whose time
half is blank is *invalid*, so `.value` is an empty string rather than a partial date. Filling
in only the date — which is all a bill needs — therefore sent null.

The form is a plain date picker now. These tests pin the server side of the contract so a
future change cannot quietly drop the date instead: a bill keeps the due date it was given,
whether that date is past, future, recurring, or handed to Homestead on the way in.
"""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.nodes.services import enable_node


def _admin() -> User:
    user = User.objects.create_user(
        username="billadmin", display_name="Bill admin", role=User.Role.ADMIN, password="pass123!"
    )
    user.set_pin("1234")
    user.save()
    return user


class BillDueDateTests(TestCase):
    def setUp(self):
        self.admin = _admin()
        enable_node(self.admin, "solace")
        enable_node(self.admin, "homestead")
        self.client.force_login(self.admin)
        self.client.post(
            reverse("auth-reauth"), {"password": "pass123!"}, content_type="application/json"
        )

    def _create(self, **extra):
        payload = {"name": "Electricity", "amount": "100.00", "is_all_day": True, "is_active": True}
        payload.update(extra)
        return self.client.post(
            reverse("solace-bill-list"), payload, content_type="application/json"
        )

    def test_future_due_date_persists(self):
        due = timezone.now() + timezone.timedelta(days=10)
        response = self._create(due_at=due.isoformat())
        self.assertEqual(response.status_code, 201)
        self.assertIsNotNone(response.json()["due_at"])

    def test_past_due_date_persists(self):
        """Bills are often entered after the fact; a past date is a real answer, not a mistake."""
        due = timezone.now() - timezone.timedelta(days=30)
        response = self._create(due_at=due.isoformat())
        self.assertEqual(response.status_code, 201)
        self.assertIsNotNone(response.json()["due_at"])

    def test_recurring_bill_keeps_its_first_due_date(self):
        due = timezone.now() - timezone.timedelta(days=30)
        response = self._create(due_at=due.isoformat(), recurrence_rule="FREQ=MONTHLY")
        self.assertEqual(response.status_code, 201)
        self.assertIsNotNone(response.json()["due_at"])
        self.assertIsNotNone(response.json()["next_due_at"])

    def test_due_date_survives_being_organised_into_homestead(self):
        """The Bills form picks a Homestead destination from the category automatically."""
        due = timezone.now() + timezone.timedelta(days=10)
        response = self._create(
            due_at=due.isoformat(), category="insurance", home_destination="insurance_policy"
        )
        self.assertEqual(response.status_code, 201)
        self.assertIsNotNone(response.json()["due_at"])

    def test_due_date_can_be_added_to_an_existing_bill(self):
        """The owner's second attempt: setting a date on a bill saved without one."""
        created = self._create()
        self.assertEqual(created.status_code, 201)
        self.assertIsNone(created.json()["due_at"])

        due = timezone.now() + timezone.timedelta(days=14)
        response = self.client.patch(
            reverse("solace-bill-detail", args=[created.json()["id"]]),
            {"due_at": due.isoformat()},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.json()["due_at"])


class BillHistorySettlementTests(TestCase):
    """Entering an existing bill must not invent a backlog of overdue payments.

    A household types the real first due date of a bill it has been paying for years. Those
    past months are history, not arrears (owner, 2026-08-09).
    """

    def setUp(self):
        self.admin = _admin()
        enable_node(self.admin, "solace")
        self.client.force_login(self.admin)
        self.client.post(
            reverse("auth-reauth"), {"password": "pass123!"}, content_type="application/json"
        )

    def _create(self, **extra):
        payload = {"name": "Electricity", "amount": "100.00", "is_all_day": True, "is_active": True}
        payload.update(extra)
        return self.client.post(
            reverse("solace-bill-list"), payload, content_type="application/json"
        )

    def test_backdated_recurring_bill_is_not_overdue(self):
        from apps.solace.models import Bill, BillOccurrence

        due = timezone.now() - timezone.timedelta(days=90)
        response = self._create(due_at=due.isoformat(), recurrence_rule="FREQ=MONTHLY")
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.json()["is_overdue"], "a newly entered bill has no arrears")

        bill = Bill.objects.get(pk=response.json()["id"])
        past = BillOccurrence.objects.filter(bill=bill, due_at__lt=timezone.now())
        self.assertTrue(past.exists(), "past occurrences should still be recorded as history")
        self.assertFalse(
            past.filter(status=BillOccurrence.Status.UPCOMING).exists(),
            "no past occurrence may still be waiting to be paid",
        )

    def test_settled_history_is_marked_paid_on_its_own_due_date(self):
        from apps.solace.models import Bill, BillOccurrence

        due = timezone.now() - timezone.timedelta(days=60)
        response = self._create(due_at=due.isoformat(), recurrence_rule="FREQ=MONTHLY")
        bill = Bill.objects.get(pk=response.json()["id"])
        occurrence = BillOccurrence.objects.filter(
            bill=bill, due_at__lt=timezone.now()
        ).order_by("due_at").first()
        self.assertEqual(occurrence.status, BillOccurrence.Status.PAID)
        self.assertEqual(occurrence.paid_at, occurrence.due_at)

    def test_future_occurrences_still_need_paying(self):
        from apps.solace.models import Bill, BillOccurrence

        due = timezone.now() - timezone.timedelta(days=60)
        response = self._create(due_at=due.isoformat(), recurrence_rule="FREQ=MONTHLY")
        bill = Bill.objects.get(pk=response.json()["id"])
        self.assertTrue(
            BillOccurrence.objects.filter(
                bill=bill, due_at__gt=timezone.now(), status=BillOccurrence.Status.UPCOMING
            ).exists(),
            "the bill must still track what is coming",
        )

    def test_a_bill_that_falls_due_later_still_goes_overdue(self):
        """Settlement applies only at entry; a genuinely missed payment must still show."""
        from apps.solace.models import Bill, BillOccurrence

        due = timezone.now() + timezone.timedelta(days=5)
        response = self._create(due_at=due.isoformat())
        bill = Bill.objects.get(pk=response.json()["id"])
        occurrence = BillOccurrence.objects.filter(bill=bill).first()
        occurrence.due_at = timezone.now() - timezone.timedelta(days=1)
        occurrence.save(update_fields=["due_at"])
        self.assertTrue(occurrence.is_overdue)


class SettleBillHistoryCommandTests(TestCase):
    """The one-off repair for bills entered before settlement existed.

    Bills created from v0.23.5 settle their own history; these are the ones already saved with
    years of arrears the household never actually owed.
    """

    def setUp(self):
        self.admin = _admin()
        enable_node(self.admin, "solace")

    def _backdated_bill_with_arrears(self):
        """A bill as it looked before v0.23.5: past occurrences left waiting to be paid."""
        from apps.solace.models import BillOccurrence
        from apps.solace.services import create_bill

        bill = create_bill(
            self.admin,
            name="Rent",
            amount="800.00",
            due_at=timezone.now() - timezone.timedelta(days=120),
            recurrence_rule="FREQ=MONTHLY",
        )
        BillOccurrence.objects.filter(bill=bill, due_at__lt=bill.created_at).update(
            status=BillOccurrence.Status.UPCOMING, paid_at=None
        )
        return bill

    def _stale(self, bill):
        from apps.solace.models import BillOccurrence

        return BillOccurrence.objects.filter(
            bill=bill, status=BillOccurrence.Status.UPCOMING, due_at__lt=bill.created_at
        )

    def test_dry_run_changes_nothing(self):
        from django.core.management import call_command
        from io import StringIO

        bill = self._backdated_bill_with_arrears()
        before = self._stale(bill).count()
        self.assertGreater(before, 0)

        out = StringIO()
        call_command("settle_bill_history", stdout=out)
        self.assertIn("Would settle", out.getvalue())
        self.assertEqual(self._stale(bill).count(), before, "a dry run must not write")

    def test_apply_settles_pre_entry_arrears(self):
        from django.core.management import call_command
        from io import StringIO

        bill = self._backdated_bill_with_arrears()
        call_command("settle_bill_history", "--apply", stdout=StringIO())
        self.assertEqual(self._stale(bill).count(), 0)

    def test_apply_leaves_payments_missed_since_entry_alone(self):
        """A bill you have been tracking and genuinely have not paid must stay overdue."""
        from apps.solace.models import Bill, BillOccurrence
        from apps.solace.services import create_bill
        from django.core.management import call_command
        from io import StringIO

        # Entered a month ago and due since — the payment fell due while you were tracking it,
        # which is the boundary the command must not cross.
        bill = create_bill(
            self.admin, name="Water", amount="60.00",
            due_at=timezone.now() - timezone.timedelta(days=2),
        )
        Bill.objects.filter(pk=bill.pk).update(
            created_at=timezone.now() - timezone.timedelta(days=30)
        )
        bill.refresh_from_db()
        occurrence = BillOccurrence.objects.get(bill=bill)
        occurrence.status = BillOccurrence.Status.UPCOMING
        occurrence.paid_at = None
        occurrence.save(update_fields=["status", "paid_at"])

        call_command("settle_bill_history", "--apply", stdout=StringIO())
        occurrence.refresh_from_db()
        self.assertEqual(occurrence.status, BillOccurrence.Status.UPCOMING)
        self.assertTrue(occurrence.is_overdue)

    def test_apply_is_idempotent(self):
        from django.core.management import call_command
        from io import StringIO

        self._backdated_bill_with_arrears()
        call_command("settle_bill_history", "--apply", stdout=StringIO())
        out = StringIO()
        call_command("settle_bill_history", "--apply", stdout=out)
        self.assertIn("Nothing to settle", out.getvalue())
