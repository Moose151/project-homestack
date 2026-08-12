"""books domain events published to the event bus (D4)."""
from apps.events.bus import publish


def entry_finished(entry_id: int, household_id: int) -> None:
    publish("books.entry_finished", payload={"entry_id": entry_id, "household_id": household_id})
