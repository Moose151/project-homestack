"""solace services — write operations for the native finance node."""
from __future__ import annotations

from datetime import date
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.scheduling.helpers import delete_event_for, sync_event_for
from apps.solace import events
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


_BILL_FIELDS = {
    "name", "category", "provider", "amount", "due_at", "is_all_day", "recurrence_rule",
    "end_date", "is_active", "is_autopay", "include_in_set_aside", "is_paid", "paid_at", "notes",
    "source_node", "source_record_type",
    "source_record_id", "visibility", "sensitivity",
}
_PAYDAY_FIELDS = {
    "title", "expected_amount", "pay_at", "is_all_day", "recurrence_rule", "received_at",
    "is_active", "notes", "visibility", "sensitivity",
}
_PURCHASE_FIELDS = {
    "name", "category", "target_amount", "saved_amount", "target_date", "is_all_day",
    "status", "priority", "notes", "visibility", "sensitivity",
}
_BUCKET_FIELDS = {
    "name", "category", "target_amount", "current_amount", "allocation_method",
    "allocation_value", "rounding_increment", "cap_to_remaining", "is_active", "position",
    "notes", "visibility", "sensitivity",
}
_SUBSCRIPTION_FIELDS = {
    "name", "provider", "amount", "billing_cycle", "next_renewal_at", "is_all_day",
    "recurrence_rule", "is_active", "notes", "visibility", "sensitivity",
}
_CHECKLIST_FIELDS = {
    "title", "cycle_start", "source_key", "bucket_id", "bill_id", "amount_hint", "position",
    "is_complete", "completed_at", "notes", "visibility", "sensitivity",
}
_SETTINGS_FIELDS = {
    "currency_symbol", "budget_year", "default_buffer_amount",
    "cycle_anchor_date", "payday_bill_handling", "show_help_tips",
    "dashboard_reminders", "due_soon_days",
}
_CATEGORY_FIELDS = {"name", "category_type", "is_active", "position", "visibility", "sensitivity"}
_BALANCE_FIELDS = {"snapshot_date", "balance", "notes", "visibility", "sensitivity"}


def get_or_create_settings(acting_user: User) -> SolaceSettings:
    household = get_active_household()
    obj, _ = SolaceSettings.objects.get_or_create(
        household=household,
        defaults={"created_by": acting_user, "updated_by": acting_user},
    )
    return obj


def update_settings(acting_user: User, obj: SolaceSettings, **data) -> SolaceSettings:
    for key, val in data.items():
        if key in _SETTINGS_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    return obj


def create_category(acting_user: User, **data) -> FinanceCategory:
    obj = FinanceCategory(
        household=get_active_household(),
        created_by=acting_user,
        updated_by=acting_user,
        **data,
    )
    obj.save()
    return obj


def update_category(acting_user: User, obj: FinanceCategory, **data) -> FinanceCategory:
    old_name = obj.name
    for key, val in data.items():
        if key in _CATEGORY_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    with transaction.atomic():
        obj.save()
        if old_name != obj.name:
            Bill.objects.filter(category=old_name).update(category=obj.name, updated_by=acting_user)
            PlannedPurchase.objects.filter(category=old_name).update(
                category=obj.name,
                updated_by=acting_user,
            )
    return obj


def delete_category(acting_user: User, obj: FinanceCategory) -> None:
    fallback = FinanceCategory.objects.filter(name="other").exclude(pk=obj.pk).first()
    fallback_name = fallback.name if fallback else "other"
    with transaction.atomic():
        Bill.objects.filter(category=obj.name).update(category=fallback_name, updated_by=acting_user)
        PlannedPurchase.objects.filter(category=obj.name).update(
            category=fallback_name,
            updated_by=acting_user,
        )
        obj.updated_by = acting_user
        obj.save(update_fields=["updated_by", "updated_at"])
        obj.soft_delete()


def create_balance_snapshot(acting_user: User, **data) -> AccountBalanceSnapshot:
    obj = AccountBalanceSnapshot(
        household=get_active_household(),
        created_by=acting_user,
        updated_by=acting_user,
        **data,
    )
    obj.save()
    return obj


def update_balance_snapshot(
    acting_user: User,
    obj: AccountBalanceSnapshot,
    **data,
) -> AccountBalanceSnapshot:
    for key, val in data.items():
        if key in _BALANCE_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    return obj


def delete_balance_snapshot(acting_user: User, obj: AccountBalanceSnapshot) -> None:
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


def set_checklist_preference(
    acting_user: User,
    *,
    source_key: str,
    label: str,
    is_hidden: bool,
    reason: str = "",
) -> PaydayChecklistPreference:
    obj, _ = PaydayChecklistPreference.objects.update_or_create(
        household=get_active_household(),
        source_key=source_key,
        defaults={
            "label": label,
            "is_hidden": is_hidden,
            "reason": reason,
            "updated_by": acting_user,
        },
        create_defaults={
            "label": label,
            "is_hidden": is_hidden,
            "reason": reason,
            "created_by": acting_user,
            "updated_by": acting_user,
        },
    )
    return obj


def set_cycle_closeout(
    acting_user: User,
    *,
    cycle_start: date,
    cycle_end: date,
    closed: bool,
    notes: str = "",
) -> CycleCloseout:
    now = timezone.now()
    obj, _ = CycleCloseout.objects.update_or_create(
        household=get_active_household(),
        cycle_start=cycle_start,
        defaults={
            "cycle_end": cycle_end,
            "status": CycleCloseout.Status.CLOSED if closed else CycleCloseout.Status.OPEN,
            "closed_at": now if closed else None,
            "notes": notes,
            "updated_by": acting_user,
        },
        create_defaults={
            "cycle_end": cycle_end,
            "status": CycleCloseout.Status.CLOSED if closed else CycleCloseout.Status.OPEN,
            "closed_at": now if closed else None,
            "notes": notes,
            "created_by": acting_user,
            "updated_by": acting_user,
        },
    )
    return obj


def create_bill(acting_user: User, **data) -> Bill:
    obj = Bill(household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data)
    obj.save()
    sync_event_for(obj)
    from apps.solace.bill_schedule import ensure_bill_occurrences

    today = timezone.localdate()
    ensure_bill_occurrences(obj, today - timedelta(days=90), today + timedelta(days=550))
    events.bill_created(obj.id, obj.household_id)
    return obj


def organise_bill_in_homestead(
    acting_user: User, obj: Bill, destination: str
) -> Bill:
    """Ask Homestead to claim a finance entry as its richer source record (D4)."""
    if not destination:
        return obj
    if obj.source_node and obj.source_node != "homestead":
        raise ValueError("This bill is already managed by another node.")
    if obj.source_node == "homestead":
        if obj.source_record_type != destination:
            raise ValueError("This bill is already organised in a different Homestead area.")
        return obj
    events.homestead_record_requested(obj, acting_user.id, destination)
    obj.refresh_from_db()
    return obj


def update_bill(
    acting_user: User,
    obj: Bill,
    *,
    occurrence_scope: str = "future_unpaid",
    **data,
) -> Bill:
    schedule_changed = bool(
        {"amount", "due_at", "recurrence_rule", "end_date", "is_active"} & set(data)
    )
    for key, val in data.items():
        if key in _BILL_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    sync_event_for(obj)
    if schedule_changed:
        from apps.solace.bill_schedule import refresh_unpaid_occurrences

        refresh_unpaid_occurrences(obj, scope=occurrence_scope)
    return obj


def mark_bill_paid(acting_user: User, obj: Bill) -> Bill:
    from apps.solace.bill_schedule import ensure_bill_occurrences

    today = timezone.localdate()
    ensure_bill_occurrences(obj, today - timedelta(days=365), today + timedelta(days=550))
    occurrence = obj.occurrences.filter(status=BillOccurrence.Status.UPCOMING).first()
    if occurrence is not None:
        mark_occurrence_paid(acting_user, occurrence)
        obj.refresh_from_db()
        return obj
    obj.is_paid = True
    obj.paid_at = timezone.now()
    obj.updated_by = acting_user
    obj.save()
    sync_event_for(obj)
    events.bill_paid(obj.id, obj.household_id)
    return obj


def delete_bill(acting_user: User, obj: Bill) -> None:
    delete_event_for(obj)
    obj.occurrences.update(deleted_at=timezone.now(), updated_by=acting_user)
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


def mark_occurrence_paid(acting_user: User, obj: BillOccurrence) -> BillOccurrence:
    obj.status = BillOccurrence.Status.PAID
    obj.paid_at = timezone.now()
    obj.updated_by = acting_user
    obj.save()
    if not obj.bill.recurrence_rule:
        bill = obj.bill
        bill.is_paid = True
        bill.paid_at = obj.paid_at
        bill.updated_by = acting_user
        bill.save()
        sync_event_for(bill)
    events.bill_paid(obj.bill_id, obj.household_id)
    return obj


def mark_occurrence_unpaid(acting_user: User, obj: BillOccurrence) -> BillOccurrence:
    obj.status = BillOccurrence.Status.UPCOMING
    obj.paid_at = None
    obj.updated_by = acting_user
    obj.save()
    if not obj.bill.recurrence_rule:
        bill = obj.bill
        bill.is_paid = False
        bill.paid_at = None
        bill.updated_by = acting_user
        bill.save()
        sync_event_for(bill)
    return obj


def skip_occurrence(acting_user: User, obj: BillOccurrence) -> BillOccurrence:
    obj.status = BillOccurrence.Status.SKIPPED
    obj.paid_at = None
    obj.updated_by = acting_user
    obj.save()
    return obj


def create_payday(acting_user: User, **data) -> Payday:
    obj = Payday(household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data)
    obj.save()
    sync_event_for(obj)
    events.payday_created(obj.id, obj.household_id)
    return obj


def update_payday(acting_user: User, obj: Payday, **data) -> Payday:
    for key, val in data.items():
        if key in _PAYDAY_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    sync_event_for(obj)
    return obj


def delete_payday(acting_user: User, obj: Payday) -> None:
    delete_event_for(obj)
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


def create_purchase(acting_user: User, **data) -> PlannedPurchase:
    obj = PlannedPurchase(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    sync_event_for(obj)
    events.planned_purchase_created(obj.id, obj.household_id)
    return obj


def update_purchase(acting_user: User, obj: PlannedPurchase, **data) -> PlannedPurchase:
    for key, val in data.items():
        if key in _PURCHASE_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    sync_event_for(obj)
    return obj


@transaction.atomic
def add_purchase_savings(
    acting_user: User,
    obj: PlannedPurchase,
    amount: Decimal,
) -> PlannedPurchase:
    obj = PlannedPurchase.objects.select_for_update().get(pk=obj.pk)
    obj.saved_amount = min(
        Decimal(obj.saved_amount) + Decimal(amount),
        Decimal(obj.target_amount),
    )
    obj.updated_by = acting_user
    obj.save(update_fields=["saved_amount", "updated_by", "updated_at"])
    return obj


def delete_purchase(acting_user: User, obj: PlannedPurchase) -> None:
    delete_event_for(obj)
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


@transaction.atomic
def create_bucket(acting_user: User, **data) -> BudgetBucket:
    obj = BudgetBucket(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    if obj.cap_to_remaining:
        BudgetBucket.objects.exclude(pk=obj.pk).filter(cap_to_remaining=True).update(
            cap_to_remaining=False,
            updated_by=acting_user,
        )
    return obj


@transaction.atomic
def update_bucket(acting_user: User, obj: BudgetBucket, **data) -> BudgetBucket:
    for key, val in data.items():
        if key in _BUCKET_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    if obj.cap_to_remaining:
        BudgetBucket.objects.exclude(pk=obj.pk).filter(cap_to_remaining=True).update(
            cap_to_remaining=False,
            updated_by=acting_user,
        )
    return obj


def delete_bucket(acting_user: User, obj: BudgetBucket) -> None:
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


def create_subscription(acting_user: User, **data) -> Subscription:
    obj = Subscription(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    sync_event_for(obj)
    events.subscription_created(obj.id, obj.household_id)
    return obj


def update_subscription(acting_user: User, obj: Subscription, **data) -> Subscription:
    for key, val in data.items():
        if key in _SUBSCRIPTION_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    sync_event_for(obj)
    return obj


def delete_subscription(acting_user: User, obj: Subscription) -> None:
    delete_event_for(obj)
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


def create_checklist_item(acting_user: User, **data) -> PaydayChecklistItem:
    obj = PaydayChecklistItem(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    return obj


def update_checklist_item(acting_user: User, obj: PaydayChecklistItem, **data) -> PaydayChecklistItem:
    for key, val in data.items():
        if key in _CHECKLIST_FIELDS:
            setattr(obj, key, val)
    if "is_complete" in data and data["is_complete"] and not obj.completed_at:
        obj.completed_at = timezone.now()
    if "is_complete" in data and not data["is_complete"]:
        obj.completed_at = None
    obj.updated_by = acting_user
    obj.save()
    return obj


def delete_checklist_item(acting_user: User, obj: PaydayChecklistItem) -> None:
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


@transaction.atomic
def generate_plan_checklist(acting_user: User, plan: dict) -> list[PaydayChecklistItem]:
    """Create or refresh transfer checklist rows for one calculated pay cycle."""
    household = get_active_household()
    cycle_start = date.fromisoformat(plan["cycle_start"])
    hidden_source_keys = set(
        PaydayChecklistPreference.objects.filter(is_hidden=True).values_list("source_key", flat=True)
    )
    required = [
        {
            "source_key": "pay-plan:confirm-income",
            "title": "Confirm all expected income has arrived",
            "bucket_id": None,
            "amount": "0.00",
        },
        *[
            {
                "source_key": f"pay-plan:bucket:{row['bucket_id']}",
                "title": f"Transfer to {row['bucket_name']}",
                "bucket_id": row["bucket_id"],
                "amount": row["amount"],
            }
            for row in plan["buckets"]
        ],
        {
            "source_key": "pay-plan:review-bills",
            "title": "Review bills due before next payday",
            "bucket_id": None,
            "amount": "0.00",
        },
        {
            "source_key": "pay-plan:record-balance",
            "title": "Optional: record the bills-account balance",
            "bucket_id": None,
            "amount": "0.00",
        },
    ]
    generated = []
    for position, row in enumerate(required, start=1):
        source_key = row["source_key"]
        if source_key in hidden_source_keys:
            continue
        obj, _ = PaydayChecklistItem.objects.update_or_create(
            household=household,
            cycle_start=cycle_start,
            source_key=source_key,
            defaults={
                "title": row["title"],
                "bucket_id": row["bucket_id"],
                "amount_hint": row["amount"],
                "position": position * 10,
                "notes": (
                    f"Generated from the Solace pay-cycle plan for "
                    f"{plan['cycle_start']} to {plan['cycle_end']}."
                ),
                "updated_by": acting_user,
            },
            create_defaults={
                "title": row["title"],
                "bucket_id": row["bucket_id"],
                "amount_hint": row["amount"],
                "position": position * 10,
                "notes": (
                    f"Generated from the Solace pay-cycle plan for "
                    f"{plan['cycle_start']} to {plan['cycle_end']}."
                ),
                "created_by": acting_user,
                "updated_by": acting_user,
            },
        )
        generated.append(obj)
    return generated
