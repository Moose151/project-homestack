"""Recurring bill occurrence generation for native Solace.

Standalone Solace treated the bill as a recurrence definition and each due date as an
independent record. This module ports that behaviour while keeping Calendar mirroring on the
existing Bill record.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db import models
from django.utils import timezone

from apps.solace.models import Bill, BillOccurrence, SolaceSettings

_PENNY = Decimal("0.01")


def _rule_parts(value: str) -> dict[str, str]:
    value = (value or "").removeprefix("RRULE:")
    return {
        key.upper(): item
        for bit in value.split(";")
        if "=" in bit
        for key, item in [bit.split("=", 1)]
    }


def annual_cost(bill: Bill, *, include_inactive: bool = False) -> Decimal:
    """Annualised bill amount using the same frequency factors as standalone Solace."""
    if not bill.is_active and not include_inactive:
        return Decimal("0.00")
    parts = _rule_parts(bill.recurrence_rule)
    interval = max(1, int(parts.get("INTERVAL", "1") or 1))
    factor = {
        "WEEKLY": Decimal("52") / interval,
        "MONTHLY": Decimal("12") / interval,
        "YEARLY": Decimal("1") / interval,
    }.get(parts.get("FREQ"), Decimal("1"))
    return (Decimal(bill.amount) * factor).quantize(_PENNY, rounding=ROUND_HALF_UP)


def fortnightly_cost(bill: Bill) -> Decimal:
    return (annual_cost(bill) / Decimal("26")).quantize(_PENNY, rounding=ROUND_HALF_UP)


def _month_candidate(anchor: datetime, offset: int, day: int) -> datetime:
    month_index = anchor.year * 12 + anchor.month - 1 + offset
    year, month_zero = divmod(month_index, 12)
    month = month_zero + 1
    return anchor.replace(year=year, month=month, day=min(day, monthrange(year, month)[1]))


def _year_candidate(anchor: datetime, offset: int, month: int, day: int) -> datetime:
    year = anchor.year + offset
    return anchor.replace(
        year=year,
        month=month,
        day=min(day, monthrange(year, month)[1]),
    )


def occurrence_datetimes(bill: Bill, start: date, end: date) -> list[datetime]:
    """Return bill due datetimes in a date window, clamping month-end dates like legacy Solace."""
    if not bill.is_active or not bill.due_at or end < start:
        return []
    anchor = bill.due_at
    if timezone.is_naive(anchor):
        anchor = timezone.make_aware(anchor, timezone.get_current_timezone())
    anchor = timezone.localtime(anchor)
    tz = timezone.get_current_timezone()
    start_at = timezone.make_aware(datetime.combine(start, time.min), tz)
    end_at = timezone.make_aware(datetime.combine(end, time.max), tz)
    if bill.end_date:
        end_at = min(
            end_at,
            timezone.make_aware(datetime.combine(bill.end_date, time.max), tz),
        )
    if end_at < start_at or anchor > end_at:
        return []
    if not bill.recurrence_rule:
        return [anchor] if start_at <= anchor <= end_at else []

    parts = _rule_parts(bill.recurrence_rule)
    frequency = parts.get("FREQ")
    interval = max(1, int(parts.get("INTERVAL", "1") or 1))
    values: list[datetime] = []
    for index in range(10000):
        if frequency == "WEEKLY":
            candidate = anchor + timedelta(weeks=index * interval)
        elif frequency == "MONTHLY":
            day = int(parts.get("BYMONTHDAY", anchor.day) or anchor.day)
            candidate = _month_candidate(anchor, index * interval, day)
        elif frequency == "YEARLY":
            month = int(parts.get("BYMONTH", anchor.month) or anchor.month)
            day = int(parts.get("BYMONTHDAY", anchor.day) or anchor.day)
            candidate = _year_candidate(anchor, index * interval, month, day)
        else:
            try:
                from dateutil.rrule import rrulestr

                return list(
                    rrulestr(bill.recurrence_rule, dtstart=anchor).between(
                        start_at,
                        end_at,
                        inc=True,
                    )
                )
            except (TypeError, ValueError):
                return [anchor] if start_at <= anchor <= end_at else []
        if candidate > end_at:
            break
        if candidate >= start_at:
            values.append(candidate)
    return values


def settle_history_on_entry(bill: Bill) -> int:
    """Treat everything already due when a bill is first entered as settled.

    A household enters a bill it has been paying for years and gives its real first due date.
    Backfilling those months as "upcoming" turns a correct answer into a wall of overdue
    warnings for money that was actually paid (owner, 2026-08-09), and drags the unpaid total
    and finance health down with it.

    Only ever called when the bill is created: from then on a missed payment is genuine and
    must still show as overdue. Occurrences are recorded paid on their own due date, since
    that is the only date the household has told us about.
    """
    now = timezone.now()
    started_today = timezone.make_aware(
        datetime.combine(timezone.localdate(), time.min),
        timezone.get_current_timezone(),
    )
    return BillOccurrence.objects.filter(
        bill=bill,
        status=BillOccurrence.Status.UPCOMING,
        due_at__lt=started_today,
    ).update(status=BillOccurrence.Status.PAID, paid_at=models.F("due_at"), updated_at=now)


def ensure_bill_occurrences(
    bill: Bill,
    start: date,
    end: date,
) -> list[BillOccurrence]:
    """Idempotently materialise one bill's occurrences in a window."""
    due_values = occurrence_datetimes(bill, start, end)
    if not due_values:
        return []
    existing = set(
        BillOccurrence.objects.filter(bill=bill, due_at__in=due_values).values_list(
            "due_at",
            flat=True,
        )
    )
    BillOccurrence.objects.bulk_create(
        [
            BillOccurrence(
                household=bill.household,
                bill=bill,
                due_at=due_at,
                amount=bill.amount,
                visibility=bill.visibility,
                sensitivity=bill.sensitivity,
                created_by=bill.created_by,
                updated_by=bill.updated_by,
            )
            for due_at in due_values
            if due_at not in existing
        ],
        ignore_conflicts=True,
    )
    return list(
        BillOccurrence.objects.filter(
            bill=bill,
            due_at__gte=timezone.make_aware(
                datetime.combine(start, time.min),
                timezone.get_current_timezone(),
            ),
            due_at__lte=timezone.make_aware(
                datetime.combine(end, time.max),
                timezone.get_current_timezone(),
            ),
        )
    )


def refresh_unpaid_occurrences(
    bill: Bill,
    *,
    scope: str = "future_unpaid",
) -> None:
    """Regenerate unpaid rows while always preserving payment history."""
    now = timezone.now()
    today = timezone.localdate()
    rows = BillOccurrence.objects.filter(bill=bill).exclude(
        status=BillOccurrence.Status.PAID
    )
    if scope == "future_unpaid":
        rows = rows.filter(due_at__gte=now)
        start = today
    elif scope == "all_unpaid":
        settings_obj = SolaceSettings.objects.first()
        budget_year = settings_obj.budget_year if settings_obj else today.year
        start = date(budget_year or today.year, 1, 1)
    else:
        raise ValueError("Unknown bill occurrence refresh scope.")
    rows.delete()
    ensure_bill_occurrences(bill, start, today + timedelta(days=550))


def refresh_future_occurrences(bill: Bill) -> None:
    """Backward-compatible default occurrence refresh."""
    refresh_unpaid_occurrences(bill, scope="future_unpaid")
