"""atlas domain events published to the event bus (D4)."""
from apps.events.bus import publish


def note_created(note_id: int, household_id: int) -> None:
    publish("atlas.note_created", payload={"note_id": note_id, "household_id": household_id})


def note_updated(note_id: int, household_id: int) -> None:
    publish("atlas.note_updated", payload={"note_id": note_id, "household_id": household_id})


def list_item_completed(item_id: int, household_id: int, completed_by_id: int) -> None:
    publish("atlas.list_item_completed", payload={
        "item_id": item_id,
        "household_id": household_id,
        "completed_by_id": completed_by_id,
    })


def reminder_created(reminder_id: int, household_id: int) -> None:
    publish("atlas.reminder_created", payload={"reminder_id": reminder_id, "household_id": household_id})
