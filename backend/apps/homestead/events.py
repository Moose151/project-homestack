"""Homestead domain events published through the thin in-process event boundary (D4)."""
from apps.events.bus import publish


def property_created(property_id: int, household_id: int) -> None:
    publish("homestead.property_created", payload={
        "property_id": property_id, "household_id": household_id,
    })


def maintenance_completed(task_id: int, household_id: int) -> None:
    publish("homestead.maintenance_completed", payload={
        "task_id": task_id, "household_id": household_id,
    })


def maintenance_saved(obj, acting_user_id: int) -> None:
    """Keep an optional Solace-funded maintenance bill aligned without sharing models."""
    if not obj.solace_bill_ref:
        return
    publish("homestead.maintenance_saved", payload={
        "source_record_type": "maintenance",
        "source_record_id": obj.id,
        "household_id": obj.household_id,
        "acting_user_id": acting_user_id,
        "solace_bill_ref": obj.solace_bill_ref,
        "name": obj.title,
        "provider": obj.provider.name if obj.provider_id else "",
        "due_at": obj.next_due_at.isoformat() if obj.next_due_at else None,
        "recurrence_rule": obj.recurrence_rule,
        "notes": obj.notes,
    })


def maintenance_deleted(obj, acting_user_id: int) -> None:
    if not obj.solace_bill_ref:
        return
    publish("homestead.maintenance_deleted", payload={
        "source_record_type": "maintenance",
        "source_record_id": obj.id,
        "household_id": obj.household_id,
        "acting_user_id": acting_user_id,
        "solace_bill_ref": obj.solace_bill_ref,
    })


def maintenance_cost_requested(
    obj, acting_user_id: int, *, amount, category: str
) -> None:
    """Ask Solace to create/update the one financial record for this task (D4)."""
    publish("homestead.maintenance_cost_requested", payload={
        "source_record_type": "maintenance",
        "source_record_id": obj.id,
        "household_id": obj.household_id,
        "acting_user_id": acting_user_id,
        "name": obj.title,
        "provider": obj.provider.name if obj.provider_id else "",
        "amount": str(amount),
        "category": category,
        "due_at": obj.next_due_at.isoformat() if obj.next_due_at else None,
        "recurrence_rule": obj.recurrence_rule,
        "is_active": True,
        "notes": obj.notes,
    })


def appliance_added(appliance_id: int, household_id: int) -> None:
    publish("homestead.appliance_added", payload={
        "appliance_id": appliance_id, "household_id": household_id,
    })


def improvement_created(improvement_id: int, household_id: int) -> None:
    publish("homestead.improvement_created", payload={
        "improvement_id": improvement_id, "household_id": household_id,
    })


def improvement_completed(improvement_id: int, household_id: int) -> None:
    publish("homestead.improvement_completed", payload={
        "improvement_id": improvement_id, "household_id": household_id,
    })


def room_created(room_id: int, household_id: int) -> None:
    publish("homestead.room_created", payload={
        "room_id": room_id, "household_id": household_id,
    })


def room_item_created(item_id: int, room_id: int, household_id: int) -> None:
    publish("homestead.room_item_created", payload={
        "item_id": item_id, "room_id": room_id, "household_id": household_id,
    })


def room_item_completed(item_id: int, room_id: int, household_id: int) -> None:
    publish("homestead.room_item_completed", payload={
        "item_id": item_id, "room_id": room_id, "household_id": household_id,
    })


_CYCLE_RRULE = {
    "weekly": "FREQ=WEEKLY",
    "fortnightly": "FREQ=WEEKLY;INTERVAL=2",
    "monthly": "FREQ=MONTHLY",
    "quarterly": "FREQ=MONTHLY;INTERVAL=3",
    "half_yearly": "FREQ=MONTHLY;INTERVAL=6",
    "yearly": "FREQ=YEARLY",
}


def _finance_payload(obj, acting_user_id: int, record_type: str, **extra) -> dict:
    amount = extra.pop("amount")
    due_at = extra.pop("due_at", None)
    return {
        "source_record_type": record_type,
        "source_record_id": obj.id,
        "household_id": obj.household_id,
        "acting_user_id": acting_user_id,
        "name": obj.name,
        "provider": obj.provider,
        "amount": str(amount),
        "due_at": due_at.isoformat() if due_at else None,
        "recurrence_rule": (
            obj.recurrence_rule or _CYCLE_RRULE.get(obj.billing_cycle, "")
        ),
        "is_active": obj.is_active,
        "notes": obj.notes,
        **extra,
    }


def insurance_policy_saved(obj, acting_user_id: int) -> None:
    publish(
        "homestead.insurance_policy_saved",
        payload=_finance_payload(
            obj,
            acting_user_id,
            "insurance_policy",
            amount=obj.premium_amount,
            due_at=obj.next_renewal_at,
            category="insurance",
        ),
    )


def household_cost_saved(obj, acting_user_id: int) -> None:
    categories = {
        "rates": "council",
        "mortgage": "mortgage",
    }
    publish(
        "homestead.household_cost_saved",
        payload=_finance_payload(
            obj,
            acting_user_id,
            "household_cost",
            amount=obj.amount,
            due_at=obj.next_due_at,
            category=categories.get(obj.cost_type, "utilities"),
        ),
    )


def home_finance_record_deleted(
    record_type: str, record_id: int, household_id: int, acting_user_id: int
) -> None:
    publish(
        "homestead.home_finance_record_deleted",
        payload={
            "source_record_type": record_type,
            "source_record_id": record_id,
            "household_id": household_id,
            "acting_user_id": acting_user_id,
        },
    )


def solace_bill_linked(
    *, bill_id: int, record_type: str, record_id: int, household_id: int,
    acting_user_id: int,
) -> None:
    publish("homestead.solace_bill_linked", payload={
        "bill_id": bill_id,
        "source_record_type": record_type,
        "source_record_id": record_id,
        "household_id": household_id,
        "acting_user_id": acting_user_id,
    })


def pool_saved(obj, acting_user_id: int) -> None:
    publish("homestead.pool_saved", payload={
        "pool_id": obj.id,
        "name": obj.name,
        "sanitiser": obj.sanitiser,
        "household_id": obj.household_id,
        "acting_user_id": acting_user_id,
    })


def pool_deleted(obj, acting_user_id: int) -> None:
    publish("homestead.pool_deleted", payload={
        "pool_id": obj.id,
        "household_id": obj.household_id,
        "acting_user_id": acting_user_id,
    })


def utility_bill_logged(obj, acting_user_id: int) -> None:
    publish("homestead.utility_bill_logged", payload={
        "utility_bill_id": obj.id,
        "utility_type": obj.utility_type,
        "period_start": obj.period_start.isoformat(),
        "period_end": obj.period_end.isoformat(),
        "usage_amount": str(obj.usage_amount),
        "usage_unit": obj.usage_unit,
        "amount": str(obj.amount),
        "household_id": obj.household_id,
        "acting_user_id": acting_user_id,
    })


def water_test_logged(obj, acting_user_id: int) -> None:
    publish("homestead.water_test_logged", payload={
        "water_test_id": obj.id,
        "pool_id": obj.pool_id,
        "tested_at": obj.tested_at.isoformat(),
        "household_id": obj.household_id,
        "acting_user_id": acting_user_id,
    })
