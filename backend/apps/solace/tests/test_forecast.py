"""Account cash flow is independent of set-aside budgeting preferences."""
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import TestCase

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.solace.bill_schedule import ensure_bill_occurrences
from apps.solace.forecast import build_balance_forecast
from apps.solace.models import AccountBalanceSnapshot, Bill, BillOccurrence, BudgetBucket, Payday


class BillsAccountForecastTests(TestCase):
    def setUp(self):
        self.household = get_active_household()
        self.household.timezone = "Australia/Brisbane"
        self.household.save()
        self.user = User.objects.create_user(username="forecast", display_name="Forecast", role=User.Role.ADMIN)
        self.tz = ZoneInfo(self.household.timezone)
        self.as_of = date(2028, 8, 3)

    def at(self, day, month=8, hour=0):
        return datetime(2028, month, day, hour, tzinfo=self.tz)

    def bill(self, **kwargs):
        return Bill.objects.create(household=self.household, name="Mortgage", amount="600",
                                   due_at=kwargs.pop("due_at", self.at(10)), **kwargs)

    def balance(self, day=2, amount="1000"):
        return AccountBalanceSnapshot.objects.create(household=self.household,
                                                     snapshot_date=date(2028, 8, day), balance=amount)

    def forecast(self):
        return build_balance_forecast(self.user, as_of=self.as_of, horizon_months=1)

    def test_mortgage_counts_even_when_not_in_set_aside(self):
        self.bill(include_in_set_aside=False, is_autopay=True, recurrence_rule="FREQ=WEEKLY;INTERVAL=2")
        self.balance()
        forecast = self.forecast()
        self.assertEqual(forecast["total_bills"], "1200.00")
        self.assertEqual(forecast["shortfall"], "200.00")
        self.assertEqual(forecast["first_shortfall_date"], "2028-08-24")
        self.assertEqual(forecast["bill_coverage"][0]["payment_count"], 2)

    def test_only_explicit_payment_account_setting_excludes_bill(self):
        self.bill(paid_from_bills_account=False, include_in_set_aside=True)
        forecast = self.forecast()
        self.assertEqual(forecast["total_bills"], "0.00")
        self.assertEqual(forecast["bill_coverage"][0]["reason"], "Paid from another account")

    def test_missing_dates_and_paused_bills_are_explained(self):
        self.bill(due_at=None)
        self.bill(is_active=False)
        forecast = self.forecast()
        self.assertEqual(forecast["total_bills"], "0.00")
        self.assertEqual({row["reason"] for row in forecast["bill_coverage"]}, {"Missing due date", "Paused"})
        self.assertTrue(any("no due date" in message for message in forecast["warnings"]))

    def test_old_snapshot_includes_intervening_payments(self):
        self.balance(day=1)
        self.bill(due_at=self.at(2))
        forecast = self.forecast()
        self.assertEqual(forecast["forecast_start"], "2028-08-02")
        self.assertEqual(forecast["ending_balance"], "400.00")

    def test_early_payment_already_in_snapshot_is_not_charged_twice(self):
        bill = self.bill()
        self.balance()
        BillOccurrence.objects.create(household=self.household, bill=bill, due_at=bill.due_at,
                                      amount=bill.amount, status="paid", paid_at=self.at(1))
        self.assertEqual(self.forecast()["total_bills"], "0.00")

    def test_payment_after_snapshot_uses_actual_payment_date_even_for_later_due_date(self):
        bill = self.bill(due_at=self.at(10, month=10))
        self.balance(day=1)
        BillOccurrence.objects.create(household=self.household, bill=bill, due_at=bill.due_at,
                                      amount=bill.amount, status="paid", paid_at=self.at(2))
        forecast = self.forecast()
        self.assertEqual(forecast["total_bills"], "600.00")
        self.assertEqual(forecast["timeline"][0]["date"], "2028-08-02")

    def test_overdue_debt_is_carried_forward_but_paid_and_skipped_are_not(self):
        self.balance()
        for status in ["upcoming", "paid", "skipped"]:
            bill = self.bill(due_at=self.at(1))
            BillOccurrence.objects.create(household=self.household, bill=bill, due_at=bill.due_at,
                                          amount=bill.amount, status=status,
                                          paid_at=self.at(1) if status == "paid" else None)
        forecast = self.forecast()
        self.assertEqual(forecast["total_bills"], "600.00")
        self.assertEqual(forecast["overdue_total"], "600.00")
        self.assertEqual(forecast["timeline"][0]["date"], "2028-08-03")

    def test_end_date_and_skipped_future_occurrence_are_respected(self):
        bill = self.bill(recurrence_rule="FREQ=WEEKLY", end_date=date(2028, 8, 17))
        ensure_bill_occurrences(bill, self.as_of, date(2028, 9, 3))
        BillOccurrence.objects.filter(bill=bill, due_at=self.at(17)).update(status="skipped")
        self.assertEqual(self.forecast()["total_bills"], "600.00")

    def test_pausing_schedule_does_not_erase_payments_since_snapshot(self):
        bill = self.bill(is_active=False)
        self.balance(day=1)
        BillOccurrence.objects.create(household=self.household, bill=bill, due_at=bill.due_at,
                                      amount=bill.amount, status="paid", paid_at=self.at(2))
        forecast = self.forecast()
        self.assertEqual(forecast["ending_balance"], "400.00")
        self.assertEqual(forecast["bill_coverage"][0]["reason"], "Included")

    def test_paydays_use_household_date_across_utc_midnight(self):
        self.balance()
        Payday.objects.create(household=self.household, title="Pay", expected_amount="1000",
                              pay_at=self.at(3), recurrence_rule="")
        BudgetBucket.objects.create(household=self.household, name="Bills", purpose="bills",
                                    allocation_method="percentage", allocation_value=Decimal("50"))
        self.bill(due_at=self.at(3))
        forecast = self.forecast()
        self.assertEqual(forecast["total_contributions"], "500.00")
        self.assertEqual(len(forecast["timeline"]), 1)
        self.assertEqual(forecast["timeline"][0]["date"], "2028-08-03")
        self.assertEqual(forecast["ending_balance"], "900.00")

    def test_inaccessible_bill_names_do_not_leak_through_coverage(self):
        other = User.objects.create_user(username="other", display_name="Other", role=User.Role.ADMIN)
        self.bill(visibility="private", created_by=other)
        self.user.role = User.Role.USER
        forecast = self.forecast()
        self.assertEqual(forecast["bill_coverage"], [])
        self.assertEqual(forecast["total_bills"], "0.00")
