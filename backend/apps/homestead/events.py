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
