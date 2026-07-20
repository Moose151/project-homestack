"""homestead domain events published to the event bus (D4, Node Spec 25).

Publish-only in V1. Homestead is designed to *consume* future events too — e.g. `solace_*`
(bills/rates) and `project_*` (house projects) — via a handler that keeps lightweight references
and deep-links back, never importing another node's models. Those consumers are wired when the
source nodes exist.
"""
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
