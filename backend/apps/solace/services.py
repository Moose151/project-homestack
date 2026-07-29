"""solace services — write operations for the native finance node."""
from __future__ import annotations

from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.scheduling.helpers import delete_event_for, sync_event_for
from apps.solace import events
from apps.solace.models import (
    Bill,
    BudgetBucket,
    Payday,
    PaydayChecklistItem,
    PlannedPurchase,
    Subscription,
)


_BILL_FIELDS = {
    "name", "category", "provider", "amount", "due_at", "is_all_day", "recurrence_rule",
    "is_paid", "paid_at", "notes", "source_node", "source_record_type",
    "source_record_id", "visibility", "sensitivity",
}
_PAYDAY_FIELDS = {
    "title", "expected_amount", "pay_at", "is_all_day", "recurrence_rule", "received_at",
    "notes", "visibility", "sensitivity",
}
_PURCHASE_FIELDS = {
    "name", "category", "target_amount", "saved_amount", "target_date", "is_all_day",
    "status", "priority", "notes", "visibility", "sensitivity",
}
_BUCKET_FIELDS = {
    "name", "category", "target_amount", "current_amount", "notes", "visibility", "sensitivity",
}
_SUBSCRIPTION_FIELDS = {
    "name", "provider", "amount", "billing_cycle", "next_renewal_at", "is_all_day",
    "recurrence_rule", "is_active", "notes", "visibility", "sensitivity",
}
_CHECKLIST_FIELDS = {
    "title", "bucket_id", "bill_id", "amount_hint", "position", "is_complete",
    "completed_at", "notes", "visibility", "sensitivity",
}


def create_bill(acting_user: User, **data) -> Bill:
    obj = Bill(household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data)
    obj.save()
    sync_event_for(obj)
    events.bill_created(obj.id, obj.household_id)
    return obj


def update_bill(acting_user: User, obj: Bill, **data) -> Bill:
    for key, val in data.items():
        if key in _BILL_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    sync_event_for(obj)
    return obj


def mark_bill_paid(acting_user: User, obj: Bill) -> Bill:
    obj.is_paid = True
    obj.paid_at = timezone.now()
    obj.updated_by = acting_user
    obj.save()
    sync_event_for(obj)
    events.bill_paid(obj.id, obj.household_id)
    return obj


def delete_bill(acting_user: User, obj: Bill) -> None:
    delete_event_for(obj)
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


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


def delete_purchase(acting_user: User, obj: PlannedPurchase) -> None:
    delete_event_for(obj)
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


def create_bucket(acting_user: User, **data) -> BudgetBucket:
    obj = BudgetBucket(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    return obj


def update_bucket(acting_user: User, obj: BudgetBucket, **data) -> BudgetBucket:
    for key, val in data.items():
        if key in _BUCKET_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
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
