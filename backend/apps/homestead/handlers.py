"""Homestead-side consumers for lightweight cross-node references (D4)."""
from __future__ import annotations

from apps.events.bus import subscribe
from apps.homestead.models import HouseholdCost, InsurancePolicy

_connected = False


def _bill_synced(sender, *, payload: dict, **kwargs) -> None:
    models = {
        "insurance_policy": InsurancePolicy,
        "household_cost": HouseholdCost,
    }
    model = models.get(payload.get("source_record_type"))
    if model is None:
        return
    model.all_objects.filter(
        pk=payload.get("source_record_id"),
        household_id=payload.get("household_id"),
    ).update(solace_bill_ref=payload.get("solace_bill_ref"))


def connect() -> None:
    global _connected
    if _connected:
        return
    subscribe("solace.home_bill_synced", _bill_synced)
    _connected = True
