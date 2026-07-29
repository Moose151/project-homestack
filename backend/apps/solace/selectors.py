"""solace selectors — read-only finance queries (D9)."""
from __future__ import annotations

from django.db import connection
from django.db.models import Max, Q
from django.utils import timezone

from apps.permissions.visibility import apply_visibility
from apps.solace.models import (
    Bill,
    BillOccurrence,
    BudgetBucket,
    Payday,
    PaydayChecklistItem,
    PlannedPurchase,
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
    qs = Bill.objects.order_by("due_at", "name")
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


def get_bill(pk: int) -> Bill | None:
    return Bill.objects.filter(pk=pk).first()


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


def get_purchase(pk: int) -> PlannedPurchase | None:
    return PlannedPurchase.objects.filter(pk=pk).first()


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
    limit: int | None = None,
):
    qs = PaydayChecklistItem.objects.select_related("bucket", "bill").order_by(
        "-cycle_start", "is_complete", "position", "title"
    )
    if incomplete_only:
        qs = qs.filter(is_complete=False)
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


def get_pay_cycle_plan(user, *, as_of=None) -> dict:
    from apps.solace.budget_engine import build_pay_cycle_plan

    return build_pay_cycle_plan(
        list_paydays(user, active_only=True),
        list_buckets(user, active_only=True),
        as_of=as_of,
    )


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
