"""Pay-cycle calculations ported from the standalone Project Solace logic.

The engine is deliberately side-effect free. Selectors supply already-authorised records and
services turn a calculated plan into checklist rows.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

from apps.solace.models import BudgetBucket, Payday

_PENNY = Decimal("0.01")


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(_PENNY, rounding=ROUND_HALF_UP)


def _money_string(value) -> str:
    return f"{_money(value):.2f}"


def _round_to_increment(value: Decimal, increment: Decimal) -> Decimal:
    increment = _money(increment)
    if increment <= 0:
        return _money(value)
    units = (value / increment).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return _money(units * increment)


def _day_bounds(start: date, end: date) -> tuple[datetime, datetime]:
    tz = timezone.get_current_timezone()
    return (
        timezone.make_aware(datetime.combine(start, time.min), tz),
        timezone.make_aware(datetime.combine(end, time.max), tz),
    )


def payday_occurrences(payday: Payday, cycle_start: date, cycle_end: date) -> list[datetime]:
    if not payday.pay_at:
        return []
    start_at, end_at = _day_bounds(cycle_start, cycle_end)
    anchor = payday.pay_at
    if timezone.is_naive(anchor):
        anchor = timezone.make_aware(anchor, timezone.get_current_timezone())
    if not payday.recurrence_rule:
        return [anchor] if start_at <= anchor <= end_at else []
    try:
        from dateutil.rrule import rrulestr

        rule = rrulestr(payday.recurrence_rule, dtstart=anchor)
        return list(rule.between(start_at, end_at, inc=True))
    except (TypeError, ValueError):
        return [anchor] if start_at <= anchor <= end_at else []


def build_pay_cycle_plan(
    paydays: list[Payday],
    buckets: list[BudgetBucket],
    *,
    as_of: date | None = None,
) -> dict:
    """Calculate a fortnightly household transfer plan.

    Percentage rules apply to each income source's pay. Fixed household rules are split
    proportionally across income sources, matching the proven standalone Solace behaviour.
    """
    as_of = as_of or timezone.localdate()
    dated_paydays = [row for row in paydays if row.pay_at]
    if dated_paydays:
        cycle_start = min(timezone.localdate(row.pay_at) for row in dated_paydays)
        while cycle_start + timedelta(days=14) <= as_of:
            cycle_start += timedelta(days=14)
    else:
        cycle_start = as_of
    cycle_end = cycle_start + timedelta(days=13)

    source_income: dict[int, Decimal] = defaultdict(lambda: Decimal("0.00"))
    source_dates: dict[int, list[str]] = defaultdict(list)
    source_rows: dict[int, Payday] = {}
    for payday in dated_paydays:
        source_rows[payday.id] = payday
        for occurrence in payday_occurrences(payday, cycle_start, cycle_end):
            source_income[payday.id] += _money(payday.expected_amount)
            source_dates[payday.id].append(occurrence.isoformat())

    household_income = _money(sum(source_income.values(), Decimal("0.00")))
    active_buckets = [bucket for bucket in buckets if bucket.is_active]
    bucket_totals: dict[int, Decimal] = defaultdict(lambda: Decimal("0.00"))
    sources = []

    for payday_id, income in sorted(
        source_income.items(),
        key=lambda item: (source_dates[item[0]][0], source_rows[item[0]].title.lower()),
    ):
        payday = source_rows[payday_id]
        allocated = Decimal("0.00")
        allocations = []
        for bucket in active_buckets:
            if bucket.allocation_method == BudgetBucket.AllocationMethod.FIXED:
                share = income / household_income if household_income else Decimal("0.00")
                raw = _money(bucket.allocation_value * share)
            else:
                raw = _money(income * bucket.allocation_value / Decimal("100"))

            amount = _round_to_increment(raw, bucket.rounding_increment)
            remaining_before = _money(income - allocated)
            capped = False
            if bucket.cap_to_remaining and amount > max(remaining_before, Decimal("0.00")):
                amount = max(remaining_before, Decimal("0.00"))
                capped = True
            allocated = _money(allocated + amount)
            bucket_totals[bucket.id] += amount
            allocations.append(
                {
                    "bucket_id": bucket.id,
                    "bucket_name": bucket.name,
                    "category": bucket.category,
                    "allocation_method": bucket.allocation_method,
                    "allocation_value": _money_string(bucket.allocation_value),
                    "raw_amount": _money_string(raw),
                    "amount": _money_string(amount),
                    "capped": capped,
                }
            )

        sources.append(
            {
                "payday_id": payday.id,
                "title": payday.title,
                "pay_dates": source_dates[payday.id],
                "income_total": _money_string(income),
                "allocated_total": _money_string(allocated),
                "remaining": _money_string(income - allocated),
                "allocations": allocations,
            }
        )

    bucket_summaries = [
        {
            "bucket_id": bucket.id,
            "bucket_name": bucket.name,
            "category": bucket.category,
            "amount": _money_string(bucket_totals[bucket.id]),
        }
        for bucket in active_buckets
        if bucket_totals[bucket.id] > 0
    ]
    allocated_total = _money(sum(bucket_totals.values(), Decimal("0.00")))
    return {
        "cycle_start": cycle_start.isoformat(),
        "cycle_end": cycle_end.isoformat(),
        "income_total": _money_string(household_income),
        "allocated_total": _money_string(allocated_total),
        "remaining": _money_string(household_income - allocated_total),
        "sources": sources,
        "buckets": bucket_summaries,
    }
