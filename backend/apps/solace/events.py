"""solace events — publish finance-domain changes via the thin event bus (D4)."""
from __future__ import annotations

from apps.events.bus import publish


def bill_created(record_id: int, household_id: int) -> None:
    publish("solace.bill_created", payload={"record_id": record_id, "household_id": household_id})


def bill_paid(record_id: int, household_id: int) -> None:
    publish("solace.bill_paid", payload={"record_id": record_id, "household_id": household_id})


def payday_created(record_id: int, household_id: int) -> None:
    publish("solace.payday_created", payload={"record_id": record_id, "household_id": household_id})


def planned_purchase_created(record_id: int, household_id: int) -> None:
    publish(
        "solace.planned_purchase_created",
        payload={"record_id": record_id, "household_id": household_id},
    )


def subscription_created(record_id: int, household_id: int) -> None:
    publish("solace.subscription_created", payload={"record_id": record_id, "household_id": household_id})


def homestead_record_requested(obj, acting_user_id: int, destination: str) -> None:
    publish("solace.homestead_record_requested", payload={
        "bill_id": obj.id,
        "household_id": obj.household_id,
        "acting_user_id": acting_user_id,
        "destination": destination,
        "name": obj.name,
        "category": obj.category,
        "provider": obj.provider,
        "amount": str(obj.amount),
        "due_at": obj.due_at.isoformat() if obj.due_at else None,
        "recurrence_rule": obj.recurrence_rule,
        "is_active": obj.is_active,
        "notes": obj.notes,
    })
