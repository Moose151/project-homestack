"""Bills-account cash-flow forecasting for native Solace."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from dateutil.relativedelta import relativedelta
from django.utils import timezone

from apps.solace import selectors
from apps.solace.bill_schedule import ensure_bill_occurrences
from apps.solace.budget_engine import build_pay_cycle_plan
from apps.solace.models import BillOccurrence

_PENNY = Decimal("0.01")


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(_PENNY, rounding=ROUND_HALF_UP)


def _money_string(value) -> str:
    return f"{_money(value):.2f}"


def _is_bills_bucket(category: str) -> bool:
    return "bill" in (category or "").casefold()


def _split_amount(amount: Decimal, count: int) -> list[Decimal]:
    """Split an amount across dated payments without losing a cent."""
    if count <= 0:
        return []
    cents = int((_money(amount) * 100).to_integral_value())
    quotient, remainder = divmod(cents, count)
    return [
        Decimal(quotient + (1 if index < remainder else 0)) / Decimal("100")
        for index in range(count)
    ]


def build_balance_forecast(
    user,
    *,
    as_of: date | None = None,
    horizon_months: int = 12,
) -> dict:
    """Project the bills account and calculate how much can safely be withdrawn.

    A snapshot recorded on ``as_of`` is treated as an end-of-day value; an older snapshot is
    the latest known current balance and receives a stale-data warning from Solace health.
    Without a snapshot, the forecast still reports the opening balance required to cover the
    projected low point.
    """
    as_of = as_of or timezone.localdate()
    horizon_months = max(1, min(int(horizon_months), 24))
    through = as_of + relativedelta(months=horizon_months)
    latest_balance = selectors.get_latest_balance(user, as_of=as_of)
    start = (
        as_of + timedelta(days=1)
        if latest_balance and latest_balance.snapshot_date == as_of
        else as_of
    )
    opening_balance = _money(latest_balance.balance) if latest_balance else None

    days: dict[date, dict] = defaultdict(
        lambda: {
            "contributions": Decimal("0.00"),
            "bills": Decimal("0.00"),
            "items": [],
        }
    )

    bills = [
        bill
        for bill in selectors.list_bills(user, active_only=True)
        if bill.include_in_set_aside and bill.due_at
    ]
    for bill in bills:
        ensure_bill_occurrences(bill, start, through)
    occurrences = selectors.list_bill_occurrences(user, start=start, end=through)
    included_bill_ids = {bill.id for bill in bills}
    for occurrence in occurrences:
        if (
            occurrence.bill_id not in included_bill_ids
            or occurrence.status == BillOccurrence.Status.SKIPPED
        ):
            continue
        # A paid occurrence still reduced a balance snapshot that predates it.
        event_date = timezone.localdate(occurrence.due_at)
        amount = _money(occurrence.amount)
        days[event_date]["bills"] += amount
        days[event_date]["items"].append(
            {
                "kind": "bill",
                "name": occurrence.bill.name,
                "amount": _money_string(amount),
                "record_id": occurrence.bill_id,
                "status": occurrence.status,
            }
        )

    settings_obj = selectors.get_settings()
    paydays = selectors.list_paydays(user, active_only=True)
    buckets = selectors.list_buckets(user, active_only=True)
    cycle_anchor = settings_obj.cycle_anchor_date if settings_obj else None
    cycle_plan = build_pay_cycle_plan(
        paydays,
        buckets,
        as_of=start,
        cycle_anchor=cycle_anchor,
    )
    cycle_start = date.fromisoformat(cycle_plan["cycle_start"])
    seen_cycles: set[date] = set()
    while cycle_start <= through and cycle_start not in seen_cycles:
        seen_cycles.add(cycle_start)
        plan = build_pay_cycle_plan(
            paydays,
            buckets,
            as_of=cycle_start,
            cycle_anchor=cycle_anchor,
        )
        for source in plan["sources"]:
            all_pay_dates = [
                datetime.fromisoformat(value).date()
                for value in source["pay_dates"]
            ]
            contribution = sum(
                (
                    _money(row["amount"])
                    for row in source["allocations"]
                    if _is_bills_bucket(row["category"])
                ),
                Decimal("0.00"),
            )
            for pay_date, amount in zip(
                all_pay_dates,
                _split_amount(contribution, len(all_pay_dates)),
            ):
                if not start <= pay_date <= through or amount <= 0:
                    continue
                days[pay_date]["contributions"] += amount
                days[pay_date]["items"].append(
                    {
                        "kind": "contribution",
                        "name": source["title"],
                        "amount": _money_string(amount),
                        "record_id": source["payday_id"],
                        "status": "expected",
                    }
                )
        cycle_start += timedelta(days=14)

    running_change = Decimal("0.00")
    minimum_change = Decimal("0.00")
    minimum_date = start
    timeline = []
    total_bills = Decimal("0.00")
    total_contributions = Decimal("0.00")
    for event_date in sorted(days):
        row = days[event_date]
        contributions = _money(row["contributions"])
        bill_total = _money(row["bills"])
        net_change = _money(contributions - bill_total)
        running_change = _money(running_change + net_change)
        total_contributions += contributions
        total_bills += bill_total
        if running_change < minimum_change:
            minimum_change = running_change
            minimum_date = event_date
        projected_balance = (
            _money(opening_balance + running_change)
            if opening_balance is not None
            else None
        )
        timeline.append(
            {
                "date": event_date.isoformat(),
                "contributions": _money_string(contributions),
                "bills": _money_string(bill_total),
                "net_change": _money_string(net_change),
                "projected_balance": (
                    _money_string(projected_balance)
                    if projected_balance is not None
                    else None
                ),
                "items": sorted(
                    row["items"],
                    key=lambda item: (item["kind"] != "contribution", item["name"].casefold()),
                ),
            }
        )

    required_opening = max(-minimum_change, Decimal("0.00"))
    buffer_amount = _money(
        settings_obj.default_buffer_amount if settings_obj else Decimal("0.00")
    )
    lowest_balance = (
        _money(opening_balance + minimum_change)
        if opening_balance is not None
        else None
    )
    ending_balance = (
        _money(opening_balance + running_change)
        if opening_balance is not None
        else None
    )
    bills_only_surplus = (
        max(lowest_balance, Decimal("0.00"))
        if lowest_balance is not None
        else None
    )
    safe_to_withdraw = (
        max(lowest_balance - buffer_amount, Decimal("0.00"))
        if lowest_balance is not None
        else None
    )
    shortfall = (
        max(-lowest_balance, Decimal("0.00"))
        if lowest_balance is not None
        else None
    )

    return {
        "as_of": as_of.isoformat(),
        "forecast_start": start.isoformat(),
        "through": through.isoformat(),
        "horizon_months": horizon_months,
        "latest_balance": latest_balance,
        "opening_balance": (
            _money_string(opening_balance) if opening_balance is not None else None
        ),
        "buffer_amount": _money_string(buffer_amount),
        "total_bills": _money_string(total_bills),
        "total_contributions": _money_string(total_contributions),
        "required_opening_balance": _money_string(required_opening),
        "ending_balance": (
            _money_string(ending_balance) if ending_balance is not None else None
        ),
        "lowest_balance": (
            _money_string(lowest_balance) if lowest_balance is not None else None
        ),
        "lowest_balance_date": minimum_date.isoformat(),
        "bills_only_surplus": (
            _money_string(bills_only_surplus)
            if bills_only_surplus is not None else None
        ),
        "safe_to_withdraw": (
            _money_string(safe_to_withdraw)
            if safe_to_withdraw is not None else None
        ),
        "shortfall": _money_string(shortfall) if shortfall is not None else None,
        "is_covered": lowest_balance >= 0 if lowest_balance is not None else None,
        "timeline": timeline,
    }
