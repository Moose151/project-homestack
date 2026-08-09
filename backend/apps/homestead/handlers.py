"""Homestead-side consumers for lightweight cross-node references (D4)."""
from __future__ import annotations

from django.utils.dateparse import parse_datetime

from apps.accounts.models import User
from apps.events.bus import subscribe
from apps.homestead import services
from apps.homestead.models import HouseholdCost, InsurancePolicy, MaintenanceTask

_connected = False


def _bill_synced(sender, *, payload: dict, **kwargs) -> None:
    models = {
        "insurance_policy": InsurancePolicy,
        "household_cost": HouseholdCost,
        "maintenance": MaintenanceTask,
    }
    model = models.get(payload.get("source_record_type"))
    if model is None:
        return
    model.all_objects.filter(
        pk=payload.get("source_record_id"),
        household_id=payload.get("household_id"),
    ).update(solace_bill_ref=payload.get("solace_bill_ref"))


def _organise_solace_bill(sender, *, payload: dict, **kwargs) -> None:
    user = User.objects.filter(pk=payload.get("acting_user_id")).first()
    if user is None:
        return
    bill = dict(payload)
    bill["due_at"] = parse_datetime(payload["due_at"]) if payload.get("due_at") else None
    services.organise_solace_bill(
        user,
        destination=payload["destination"],
        bill=bill,
    )


def connect() -> None:
    global _connected
    if _connected:
        return
    subscribe("solace.home_bill_synced", _bill_synced)
    subscribe("solace.homestead_record_requested", _organise_solace_bill)
    _connected = True
