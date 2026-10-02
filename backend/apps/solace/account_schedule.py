"""Shared bill schedule explanations for Money and its read-only Home projection."""
from datetime import timedelta

from django.utils import timezone

from apps.solace.bill_schedule import household_timezone, occurrence_datetimes


def describe_schedule(bill, *, as_of=None):
    tz = household_timezone(bill.household)
    today = as_of or timezone.localdate(timezone=tz)
    issue = None
    if not bill.is_active:
        status = "Paused"
    elif not bill.due_at:
        status = "Needs a payment date"
        issue = "Add a payment date so this bill can be included in the forecast."
    elif bill.recurrence_rule and bill.end_date and bill.end_date < today:
        status = f"Ended {bill.end_date.isoformat()}"
        issue = "This bill is active but its repeating schedule has ended. Remove the end date if payments should continue, or pause the bill."
    elif bill.recurrence_rule and bill.end_date == timezone.localdate(bill.due_at, tz):
        status = "Stops after first payment"
        issue = "The end date is the same as the first payment date. This repeating bill will only have one payment."
    else:
        status = "Repeating" if bill.recurrence_rule else "One-off"
    dates = occurrence_datetimes(bill, today, today + timedelta(days=730))[:3]
    return {"status": status, "issue": issue, "next_dates": [value.isoformat() for value in dates]}
