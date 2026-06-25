"""achievements domain events (D4)."""
from apps.events.bus import publish


def badge_earned(person_id: int, household_id: int, badge_code: str, name: str, icon: str) -> None:
    publish("achievements.badge_earned", payload={
        "person_id": person_id, "household_id": household_id,
        "badge_code": badge_code, "name": name, "icon": icon,
    })
