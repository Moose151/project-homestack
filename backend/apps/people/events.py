"""
people events — signals published via the thin events interface (D4).

No cross-node model imports. Extend here as node integrations are added.
"""
from apps.events.bus import publish


def person_deleted(person_id: int, household_id: int) -> None:
    """A Person was soft-deleted.

    Nodes that keep a per-person record (Atlas's personal To-do list) subscribe to this so they
    can retire it and rehome its contents, without `people` having to know they exist.
    """
    publish("people.person_deleted", payload={"person_id": person_id, "household_id": household_id})
