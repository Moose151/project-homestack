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
    cycle_anchor: date | None = None,
) -> dict:
    """Calculate a fortnightly household transfer plan.

    Percentage rules apply to each income source's pay. Fixed household rules are split
    proportionally across income sources, matching the proven standalone Solace behaviour.
    """
    as_of = as_of or timezone.localdate()
    dated_paydays = [row for row in paydays if row.pay_at]
    if cycle_anchor:
        cycle_start = cycle_anchor
        while cycle_start > as_of:
            cycle_start -= timedelta(days=14)
        while cycle_start + timedelta(days=14) <= as_of:
            cycle_start += timedelta(days=14)
    elif dated_paydays:
        cycle_start = min(timezone.localdate(row.pay_at) for row in dated_paydays)
        while cycle_start > as_of:
            cycle_start -= timedelta(days=14)
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

    # Individual and shared income are separated before any bucket maths: shared income belongs
    # to the household, so letting it into the percentage split would inflate personal shares.
    individual_ids = [
        pk for pk in source_income
        if source_rows[pk].income_scope != Payday.Scope.SHARED
    ]
    shared_ids = [pk for pk in source_income if pk not in individual_ids]
    individual_income = _money(sum((source_income[pk] for pk in individual_ids), Decimal("0.00")))
    shared_income = _money(sum((source_income[pk] for pk in shared_ids), Decimal("0.00")))
    household_income = _money(individual_income + shared_income)
    active_buckets = [bucket for bucket in buckets if bucket.is_active]
    bucket_totals: dict[int, Decimal] = defaultdict(lambda: Decimal("0.00"))
    sources = []
    people: dict[str, dict] = {}

    def _allocate(income: Decimal, pool_total: Decimal) -> tuple[list[dict], Decimal]:
        """Bucket rows for one slice of income, against a pool total for fixed-rule shares."""
        allocated = Decimal("0.00")
        rows = []
        # Only the first bucket allowed to cap may do so; later flags are ignored defensively,
        # matching the reference implementation even though creation keeps a single one.
        remainder_seen = False
        for bucket in active_buckets:
            if bucket.allocation_method == BudgetBucket.AllocationMethod.FIXED:
                share = income / pool_total if pool_total else Decimal("0.00")
                raw = _money(bucket.allocation_value * share)
            else:
                raw = _money(income * bucket.allocation_value / Decimal("100"))
            amount = _round_to_increment(raw, bucket.rounding_increment)
            remaining_before = _money(income - allocated)
            capped = False
            cap_enabled = bucket.cap_to_remaining and not remainder_seen
            if cap_enabled:
                remainder_seen = True
            if cap_enabled and amount > max(remaining_before, Decimal("0.00")):
                amount = max(remaining_before, Decimal("0.00"))
                capped = True
            allocated = _money(allocated + amount)
            rows.append(
                {
                    "bucket_id": bucket.id,
                    "bucket_name": bucket.name,
                    "category": bucket.category,
                    "purpose": bucket.purpose,
                    "allocation_method": bucket.allocation_method,
                    "allocation_value": _money_string(bucket.allocation_value),
                    "raw_amount": _money_string(raw),
                    "amount": _money_string(amount),
                    "capped": capped,
                }
            )
        return rows, allocated

    for payday_id in sorted(
        source_income,
        key=lambda pk: (source_dates[pk][0], source_rows[pk].title.lower()),
    ):
        payday = source_rows[payday_id]
        income = source_income[payday_id]
        is_shared = payday.income_scope == Payday.Scope.SHARED
        mode = payday.allocation_mode if is_shared else Payday.AllocationMode.STANDARD

        if is_shared and mode != Payday.AllocationMode.STANDARD:
            allocations = _shared_allocations(payday, income, active_buckets)
            for row in allocations:
                bucket_totals[row["bucket_id"]] += Decimal(row["amount"])
            allocated = _money(sum((Decimal(row["amount"]) for row in allocations), Decimal("0.00")))
        else:
            # Standard shared income joins the household pool and is split by the usual rules.
            pool = individual_income if not is_shared else income
            allocations, allocated = _allocate(income, pool)
            for row in allocations:
                bucket_totals[row["bucket_id"]] += Decimal(row["amount"])

        sources.append(
            {
                "payday_id": payday.id,
                "title": payday.title,
                "owner_name": payday.owner_name or "Household",
                "income_scope": payday.income_scope,
                "allocation_mode": mode,
                "pay_dates": source_dates[payday_id],
                "income_total": _money_string(income),
                "allocated_total": _money_string(allocated),
                "remaining": _money_string(income - allocated),
                "allocations": allocations,
            }
        )

        # Contribution breakdown covers individual income only; shared income has no owner.
        if not is_shared:
            owner = payday.owner_name or "Household"
            entry = people.setdefault(owner, {"owner_name": owner, "income": Decimal("0.00"), "titles": []})
            entry["income"] += income
            entry["titles"].append(payday.title)

    person_rows = []
    for owner in sorted(people, key=str.lower):
        entry = people[owner]
        allocations, allocated = _allocate(entry["income"], individual_income)
        person_rows.append(
            {
                "owner_name": owner,
                "income_total": _money_string(entry["income"]),
                "allocated_total": _money_string(allocated),
                "remaining": _money_string(entry["income"] - allocated),
                "sources": entry["titles"],
                "allocations": allocations,
            }
        )

    bucket_summaries = [
        {
            "bucket_id": bucket.id,
            "bucket_name": bucket.name,
            "category": bucket.category,
            "purpose": bucket.purpose,
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
        "individual_income_total": _money_string(individual_income),
        "shared_income_total": _money_string(shared_income),
        "allocated_total": _money_string(allocated_total),
        "remaining": _money_string(household_income - allocated_total),
        "sources": sources,
        "people": person_rows,
        "buckets": bucket_summaries,
    }


def _shared_allocations(payday: Payday, income: Decimal, buckets: list[BudgetBucket]) -> list[dict]:
    """Bucket rows for shared income that bypasses the usual rules.

    `lump` sends the whole amount to one bucket. `custom` applies each line's percentage in
    order, and the line marked as the remainder takes whatever is left. With no remainder line
    an unallocated amount simply stays in the account rather than being invented into a bucket.
    """
    by_id = {bucket.id: bucket for bucket in buckets}
    rows: list[dict] = []

    def _row(bucket: BudgetBucket, amount: Decimal, label: str) -> dict:
        return {
            "bucket_id": bucket.id,
            "bucket_name": bucket.name,
            "category": bucket.category,
            "purpose": bucket.purpose,
            "allocation_method": "shared",
            "allocation_value": label,
            "raw_amount": _money_string(amount),
            "amount": _money_string(amount),
            "capped": False,
        }

    if payday.allocation_mode == Payday.AllocationMode.LUMP:
        bucket = by_id.get(payday.lump_bucket_id)
        return [_row(bucket, _money(income), "All of it")] if bucket else []

    allocated = Decimal("0.00")
    remainder_bucket = None
    for line in payday.allocations.all():
        bucket = by_id.get(line.bucket_id)
        if not bucket:
            continue
        if line.is_remainder:
            remainder_bucket = bucket
            continue
        amount = _money(income * Decimal(line.percentage) / Decimal("100"))
        allocated = _money(allocated + amount)
        rows.append(_row(bucket, amount, f"{Decimal(line.percentage):g}%"))
    if remainder_bucket:
        rows.append(_row(remainder_bucket, max(_money(income - allocated), Decimal("0.00")), "Remainder"))
    return rows
