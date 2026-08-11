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


def _link_homestead_record(sender, *, payload: dict, **kwargs) -> None:
    user = User.objects.filter(pk=payload["acting_user_id"]).first()
    bill = Bill.objects.filter(
        pk=payload["bill_id"], household_id=payload["household_id"]
    ).first()
    if user is None or bill is None:
        return
    # The source fields are a navigation/display link only. Avoid the normal bill-save event
    # here because Homestead has just supplied this link and does not need its projection echoed.
    bill.source_node = "homestead"
    bill.source_record_type = payload["source_record_type"]
    bill.source_record_id = payload["source_record_id"]
    bill.updated_by = user
    bill.save(update_fields=[
        "source_node", "source_record_type", "source_record_id", "updated_by", "updated_at"
    ])


def _sync_home_maintenance_bill(sender, *, payload: dict, **kwargs) -> None:
    user = User.objects.filter(pk=payload["acting_user_id"]).first()
    bill = Bill.objects.filter(
        pk=payload["solace_bill_ref"],
        household_id=payload["household_id"],
        source_node="homestead",
        source_record_type="maintenance",
        source_record_id=payload["source_record_id"],
    ).first()
    if user is None or bill is None:
        return
    services.update_bill(
        user,
        bill,
        name=payload["name"],
        provider=payload.get("provider", ""),
        due_at=parse_datetime(payload["due_at"]) if payload.get("due_at") else None,
        recurrence_rule=payload.get("recurrence_rule", ""),
        notes=payload.get("notes", ""),
    )


def _delete_home_maintenance_bill(sender, *, payload: dict, **kwargs) -> None:
    user = User.objects.filter(pk=payload["acting_user_id"]).first()
    bill = Bill.objects.filter(
        pk=payload["solace_bill_ref"], household_id=payload["household_id"]
    ).first()
    if user is not None and bill is not None:
        services.delete_bill(user, bill)


def connect() -> None:
    global _connected
    if _connected:
        return
    # Costs & Cover is now a Solace-owned projection. The remaining Homestead-originated
    # finance events are maintenance-specific workflows.
    subscribe("homestead.solace_bill_linked", _link_homestead_record)
    subscribe("homestead.maintenance_saved", _sync_home_maintenance_bill)
    subscribe("homestead.maintenance_deleted", _delete_home_maintenance_bill)
    subscribe("homestead.maintenance_cost_requested", _sync_home_bill)
    _connected = True
