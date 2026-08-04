"""solace selectors — read-only finance queries (D9)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.db import connection
from django.db.models import Max, Prefetch, Q
from django.utils import timezone

from apps.permissions.visibility import apply_visibility
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


def _search(qs, query: str, fields: list[str]):
    if connection.vendor == "postgresql":
        from django.contrib.postgres.search import SearchQuery, SearchVector
        return qs.annotate(_search=SearchVector(*fields)).filter(_search=SearchQuery(query))
    clause = Q()
    for field in fields:
        clause |= Q(**{f"{field}__icontains": query})
    return qs.filter(clause)


def list_bills(
    user=None,
    *,
    upcoming_only: bool = False,
    unpaid_only: bool = False,
    active_only: bool = False,
    limit: int | None = None,
):
    qs = Bill.objects.prefetch_related(
        Prefetch(
            "occurrences",
            queryset=BillOccurrence.objects.filter(status=BillOccurrence.Status.UPCOMING).order_by("due_at"),
            to_attr="upcoming_occurrences",
        )
    ).order_by("due_at", "name")
    if upcoming_only:
        qs = qs.filter(due_at__isnull=False)
    if unpaid_only:
        qs = qs.filter(is_paid=False)
    if active_only:
        qs = qs.filter(is_active=True)
    if user is not None:
        qs = apply_visibility(qs, user)
    if limit is not None:
        qs = qs[:limit]
    return list(qs)


def get_bill(pk: int, user=None) -> Bill | None:
    qs = Bill.objects.filter(pk=pk)
    if user is not None:
        qs = apply_visibility(qs, user)
    return qs.first()


def get_bill_occurrence_timeline(
    user,
    bill: Bill,
    *,
    as_of: date | None = None,
    limit: int = 12,
) -> dict:
    as_of = as_of or timezone.localdate()
    qs = apply_visibility(
        BillOccurrence.objects.filter(
            bill=bill,
            bill__deleted_at__isnull=True,
        ),
        user,
    )
    return {
        "upcoming": list(qs.filter(due_at__date__gte=as_of).order_by("due_at")[:limit]),
        "history": list(qs.filter(due_at__date__lt=as_of).order_by("-due_at")[:limit]),
    }


def list_bill_occurrences(user, *, start, end, status: str = ""):
    qs = BillOccurrence.objects.select_related("bill").filter(
        bill__deleted_at__isnull=True,
        due_at__date__gte=start,
        due_at__date__lte=end,
    )
    if status:
        qs = qs.filter(status=status)
    return list(apply_visibility(qs, user).order_by("due_at", "bill__name"))


def get_bill_occurrence(user, pk: int) -> BillOccurrence | None:
    qs = BillOccurrence.objects.select_related("bill").filter(
        pk=pk,
        bill__deleted_at__isnull=True,
    )
    return apply_visibility(qs, user).first()


def list_paydays(
    user=None,
    *,
    upcoming_only: bool = False,
    active_only: bool = False,
    limit: int | None = None,
):
    qs = Payday.objects.order_by("pay_at", "title")
    if upcoming_only:
        qs = qs.filter(pay_at__isnull=False, pay_at__gte=timezone.now())
    if active_only:
        qs = qs.filter(is_active=True)
    if user is not None:
        qs = apply_visibility(qs, user)
    if limit is not None:
        qs = qs[:limit]
    return list(qs)


def get_payday(pk: int) -> Payday | None:
    return Payday.objects.filter(pk=pk).first()


def list_purchases(user=None, *, open_only: bool = False, limit: int | None = None):
    qs = PlannedPurchase.objects.order_by("target_date", "-updated_at")
    if open_only:
        qs = qs.exclude(status__in=(PlannedPurchase.Status.BOUGHT, PlannedPurchase.Status.CANCELLED))
    if user is not None:
        qs = apply_visibility(qs, user)
    if limit is not None:
        qs = qs[:limit]
    return list(qs)


def get_purchase(pk: int, user=None) -> PlannedPurchase | None:
    qs = PlannedPurchase.objects.filter(pk=pk)
    if user is not None:
        qs = apply_visibility(qs, user)
    return qs.first()


def list_buckets(user=None, *, active_only: bool = False, limit: int | None = None):
    qs = BudgetBucket.objects.order_by("position", "name")
    if active_only:
        qs = qs.filter(is_active=True)
    if user is not None:
        qs = apply_visibility(qs, user)
    if limit is not None:
        qs = qs[:limit]
    return list(qs)


def get_bucket(pk: int) -> BudgetBucket | None:
    return BudgetBucket.objects.filter(pk=pk).first()


def list_subscriptions(user=None, *, active_only: bool = False, limit: int | None = None):
    qs = Subscription.objects.order_by("next_renewal_at", "name")
    if active_only:
        qs = qs.filter(is_active=True)
    if user is not None:
        qs = apply_visibility(qs, user)
    if limit is not None:
        qs = qs[:limit]
    return list(qs)


def get_subscription(pk: int) -> Subscription | None:
    return Subscription.objects.filter(pk=pk).first()


def list_checklist_items(
    user=None,
    *,
    incomplete_only: bool = False,
    latest_cycle_only: bool = False,
    cycle_start=None,
    limit: int | None = None,
):
    qs = PaydayChecklistItem.objects.select_related("bucket", "bill").order_by(
        "-cycle_start", "is_complete", "position", "title"
    )
    hidden_source_keys = PaydayChecklistPreference.objects.filter(
        is_hidden=True
    ).values_list("source_key", flat=True)
    qs = qs.exclude(source_key__in=hidden_source_keys)
    if incomplete_only:
        qs = qs.filter(is_complete=False)
    if cycle_start is not None:
        qs = qs.filter(Q(cycle_start__isnull=True) | Q(cycle_start=cycle_start))
    if latest_cycle_only:
        latest_cycle = qs.aggregate(value=Max("cycle_start"))["value"]
        if latest_cycle:
            qs = qs.filter(Q(cycle_start__isnull=True) | Q(cycle_start=latest_cycle))
    if user is not None:
        qs = apply_visibility(qs, user)
    if limit is not None:
        qs = qs[:limit]
    return list(qs)


def get_checklist_item(pk: int) -> PaydayChecklistItem | None:
    return PaydayChecklistItem.objects.filter(pk=pk).first()


def get_settings() -> SolaceSettings | None:
    return SolaceSettings.objects.first()


def list_categories(user=None, *, active_only: bool = False, category_type: str = ""):
    qs = FinanceCategory.objects.order_by("position", "name")
    if active_only:
        qs = qs.filter(is_active=True)
    if category_type:
        qs = qs.filter(category_type__in=(category_type, FinanceCategory.CategoryType.BOTH))
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_category(pk: int) -> FinanceCategory | None:
    return FinanceCategory.objects.filter(pk=pk).first()


def list_balance_snapshots(user=None, *, limit: int | None = None):
    qs = AccountBalanceSnapshot.objects.order_by("-snapshot_date", "-id")
    if user is not None:
        qs = apply_visibility(qs, user)
    if limit is not None:
        qs = qs[:limit]
    return list(qs)


def get_balance_snapshot(pk: int) -> AccountBalanceSnapshot | None:
    return AccountBalanceSnapshot.objects.filter(pk=pk).first()


def get_latest_balance(user=None, *, as_of: date | None = None) -> AccountBalanceSnapshot | None:
    qs = AccountBalanceSnapshot.objects.order_by("-snapshot_date", "-id")
    if as_of is not None:
        qs = qs.filter(snapshot_date__lte=as_of)
    if user is not None:
        qs = apply_visibility(qs, user)
    rows = list(qs[:1])
    return rows[0] if rows else None


def list_checklist_preferences(user=None, *, hidden_only: bool = False):
    qs = PaydayChecklistPreference.objects.order_by("label")
    if hidden_only:
        qs = qs.filter(is_hidden=True)
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_cycle_closeout(cycle_start: date) -> CycleCloseout | None:
    return CycleCloseout.objects.filter(cycle_start=cycle_start).first()


def get_pay_cycle_plan(user, *, as_of=None) -> dict:
    from apps.solace.budget_engine import build_pay_cycle_plan
    from apps.solace.bill_schedule import fortnightly_cost

    settings_obj = get_settings()
    plan = build_pay_cycle_plan(
        list_paydays(user, active_only=True),
        list_buckets(user, active_only=True),
        as_of=as_of,
        cycle_anchor=settings_obj.cycle_anchor_date if settings_obj else None,
    )
    cycle_start = date.fromisoformat(plan["cycle_start"])
    penny = Decimal("0.01")
    recurring_average = sum(
        (
            fortnightly_cost(bill)
            for bill in list_bills(user, active_only=True)
            if bill.include_in_set_aside
        ),
        Decimal("0.00"),
    )
    purchase_average = Decimal("0.00")
    for purchase in list_purchases(user, open_only=True):
        remaining = max(
            Decimal(purchase.target_amount) - Decimal(purchase.saved_amount),
            Decimal("0.00"),
        )
        target = (
            timezone.localdate(purchase.target_date)
            if purchase.target_date
            else cycle_start
        )
        periods = max(1, ((target - cycle_start).days // 14) + 1)
        purchase_average += remaining / Decimal(periods)
    purchase_average = purchase_average.quantize(penny, rounding=ROUND_HALF_UP)
    buffer_amount = (
        Decimal(settings_obj.default_buffer_amount)
        if settings_obj else Decimal("0.00")
    )
    required = (recurring_average + purchase_average + buffer_amount).quantize(
        penny,
        rounding=ROUND_HALF_UP,
    )
    bills_bucket_total = sum(
        (
            Decimal(row["amount"])
            for row in plan["buckets"]
            if (
                "bill" in row["category"].casefold()
                or "planned purchase" in row["category"].casefold()
            )
        ),
        Decimal("0.00"),
    )
    shortfall = max(required - bills_bucket_total, Decimal("0.00")).quantize(
        penny,
        rounding=ROUND_HALF_UP,
    )
    plan["set_aside"] = {
        "recurring_bills": f"{recurring_average:.2f}",
        "planned_purchases": f"{purchase_average:.2f}",
        "buffer": f"{buffer_amount:.2f}",
        "required_total": f"{required:.2f}",
        "bills_bucket_total": f"{bills_bucket_total:.2f}",
        "shortfall": f"{shortfall:.2f}",
        "is_covered": shortfall == 0,
    }
    return plan


def search_solace(user, query: str) -> dict:
    bills = _search(Bill.objects.all(), query, ["name", "provider", "notes"])
    paydays = _search(Payday.objects.all(), query, ["title", "notes"])
    purchases = _search(PlannedPurchase.objects.all(), query, ["name", "category", "notes"])
    buckets = _search(BudgetBucket.objects.all(), query, ["name", "category", "notes"])
    subscriptions = _search(Subscription.objects.all(), query, ["name", "provider", "notes"])
    checklist = _search(PaydayChecklistItem.objects.all(), query, ["title", "notes"])
    if user is not None:
        bills = apply_visibility(bills, user)
        paydays = apply_visibility(paydays, user)
        purchases = apply_visibility(purchases, user)
        buckets = apply_visibility(buckets, user)
        subscriptions = apply_visibility(subscriptions, user)
        checklist = apply_visibility(checklist, user)
    return {
        "bills": list(bills.order_by("due_at", "name")),
        "paydays": list(paydays.order_by("pay_at", "title")),
        "purchases": list(purchases.order_by("target_date", "-updated_at")),
        "buckets": list(buckets.order_by("name")),
        "subscriptions": list(subscriptions.order_by("next_renewal_at", "name")),
        "checklist": list(checklist.order_by("is_complete", "position", "title")),
    }
