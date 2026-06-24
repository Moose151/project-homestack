"""meridian domain events published to the event bus (D4, Node Spec 11).

Publishes: task_created, task_completed, task_approved, task_rejected,
reward_requested, reward_approved, points_awarded.

Consumes (future milestones, wired when those nodes exist): homework_created,
pet_care_task_created, inventory_task_created, project_task_created — each creating
a rewarded Meridian task. No cross-node model imports (D4): consumption happens via
the thin events interface, not by importing Education/Pets/etc. models.
"""
from apps.events.bus import publish


def task_created(task_id: int, household_id: int) -> None:
    publish("meridian.task_created", payload={"task_id": task_id, "household_id": household_id})


def task_completed(task_id: int, household_id: int, person_id: int | None) -> None:
    publish("meridian.task_completed", payload={
        "task_id": task_id, "household_id": household_id, "person_id": person_id,
    })


def task_approved(task_id: int, household_id: int, person_id: int | None, points: int) -> None:
    publish("meridian.task_approved", payload={
        "task_id": task_id, "household_id": household_id,
        "person_id": person_id, "points": points,
    })


def task_rejected(task_id: int, household_id: int) -> None:
    publish("meridian.task_rejected", payload={"task_id": task_id, "household_id": household_id})


def reward_requested(request_id: int, household_id: int, person_id: int) -> None:
    publish("meridian.reward_requested", payload={
        "request_id": request_id, "household_id": household_id, "person_id": person_id,
    })


def reward_approved(request_id: int, household_id: int, person_id: int, points_spent: int) -> None:
    publish("meridian.reward_approved", payload={
        "request_id": request_id, "household_id": household_id,
        "person_id": person_id, "points_spent": points_spent,
    })


def points_awarded(person_id: int, household_id: int, points: int, reason: str) -> None:
    publish("meridian.points_awarded", payload={
        "person_id": person_id, "household_id": household_id,
        "points": points, "reason": reason,
    })
