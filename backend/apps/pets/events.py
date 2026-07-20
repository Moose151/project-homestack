"""pets domain events published to the event bus (D4, Node Spec 11).

Publish-only in V1. Consumers (Meridian generating a rewarded "feed the pets" task, Travel
prompting pet-sitter instructions) are wired in a later slice. Nodes never import each other's
models — they communicate via these signals.
"""
from apps.events.bus import publish


def pet_created(pet_id: int, household_id: int) -> None:
    publish("pets.pet_created", payload={"pet_id": pet_id, "household_id": household_id})


def treatment_completed(treatment_id: int, household_id: int) -> None:
    publish("pets.treatment_completed", payload={
        "treatment_id": treatment_id, "household_id": household_id,
    })


def appointment_created(appointment_id: int, household_id: int) -> None:
    publish("pets.appointment_created", payload={
        "appointment_id": appointment_id, "household_id": household_id,
    })
