"""home_wiki domain events published to the event bus (D4, Node Spec 11).

Publish-only in V1. Consumers (Assets linking a manual → reference page, etc.) are wired in a
later slice. Nodes never import each other's models — they communicate via these signals.
"""
from apps.events.bus import publish


def page_created(page_id: int, household_id: int) -> None:
    publish("home_wiki.page_created", payload={"page_id": page_id, "household_id": household_id})


def page_updated(page_id: int, household_id: int) -> None:
    publish("home_wiki.page_updated", payload={"page_id": page_id, "household_id": household_id})


def page_deleted(page_id: int, household_id: int) -> None:
    publish("home_wiki.page_deleted", payload={"page_id": page_id, "household_id": household_id})


def emergency_page_updated(page_id: int, household_id: int) -> None:
    publish("home_wiki.emergency_page_updated", payload={
        "page_id": page_id, "household_id": household_id,
    })
