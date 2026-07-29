"""Cross-node handlers for Homestead-owned home costs (D4).

Only this Solace module touches Solace models. Homestead sends primitive event payloads and
receives a lightweight reference event in return.
"""
from __future__ import annotations

from django.utils.dateparse import parse_datetime

from apps.accounts.models import User
from apps.events.bus import publish, subscribe
from apps.solace import services
from apps.solace.models import Bill

_connected = False


def _find_bill(payload: dict) -> Bill | None:
    lookup = {
        "household_id": payload["household_id"],
        "source_node": "homestead",
        "source_record_type": payload["source_record_type"],
        "source_record_id": payload["source_record_id"],
    }
    active = Bill.objects.filter(**lookup).first()
    if active is not None:
        return active
    return Bill.all_objects.filter(
        **lookup
    ).order_by("-updated_at").first()


def _sync_home_bill(sender, *, payload: dict, **kwargs) -> None:
    user = User.objects.filter(pk=payload["acting_user_id"]).first()
    if user is None:
        return

    bill = _find_bill(payload)
    if not payload.get("is_active", True):
        if bill is not None and bill.deleted_at is None:
            services.delete_bill(user, bill)
        publish(
            "solace.home_bill_synced",
            payload={
                "source_record_type": payload["source_record_type"],
                "source_record_id": payload["source_record_id"],
                "household_id": payload["household_id"],
                "solace_bill_ref": None,
            },
        )
        return

    due_at = parse_datetime(payload["due_at"]) if payload.get("due_at") else None
    data = {
        "name": payload["name"],
        "category": payload["category"],
        "provider": payload.get("provider", ""),
        "amount": payload["amount"],
        "due_at": due_at,
        "is_all_day": True,
        "recurrence_rule": payload.get("recurrence_rule", ""),
        "notes": payload.get("notes", ""),
        "source_node": "homestead",
        "source_record_type": payload["source_record_type"],
        "source_record_id": payload["source_record_id"],
        "visibility": "sensitive",
        "sensitivity": "financial",
    }
    if bill is None:
        bill = services.create_bill(user, **data)
    else:
        if bill.deleted_at is not None:
            bill.deleted_at = None
        if bill.due_at != due_at:
            data.update({"is_paid": False, "paid_at": None})
        bill = services.update_bill(user, bill, **data)

    publish(
        "solace.home_bill_synced",
        payload={
            "source_record_type": payload["source_record_type"],
            "source_record_id": payload["source_record_id"],
            "household_id": payload["household_id"],
            "solace_bill_ref": bill.id,
        },
    )


def _delete_home_bill(sender, *, payload: dict, **kwargs) -> None:
    user = User.objects.filter(pk=payload["acting_user_id"]).first()
    bill = _find_bill(payload)
    if user is not None and bill is not None and bill.deleted_at is None:
        services.delete_bill(user, bill)
    publish(
        "solace.home_bill_synced",
        payload={
            "source_record_type": payload["source_record_type"],
            "source_record_id": payload["source_record_id"],
            "household_id": payload["household_id"],
            "solace_bill_ref": None,
        },
    )


def connect() -> None:
    global _connected
    if _connected:
        return
    subscribe("homestead.insurance_policy_saved", _sync_home_bill)
    subscribe("homestead.household_cost_saved", _sync_home_bill)
    subscribe("homestead.home_finance_record_deleted", _delete_home_bill)
    _connected = True
