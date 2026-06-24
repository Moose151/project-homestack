"""scheduling domain events published to the event bus (D4)."""
from apps.events.bus import publish


def event_created(event_id: int, household_id: int) -> None:
    publish("scheduling.event_created", payload={"event_id": event_id, "household_id": household_id})


def event_updated(event_id: int, household_id: int) -> None:
    publish("scheduling.event_updated", payload={"event_id": event_id, "household_id": household_id})


def event_deleted(event_id: int, household_id: int) -> None:
    publish("scheduling.event_deleted", payload={"event_id": event_id, "household_id": household_id})
