from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from django.utils import timezone

from apps.nodes.selectors import get_household_node
from apps.people.corner_registry import providers
from apps.people.models import CornerReaction, Person
from apps.people.selectors import person_for_user


def _enabled(node_key: str) -> bool:
    config = get_household_node(node_key)
    return config is None or config.is_enabled


def build_corner(user, person: Person, *, days: int = 30) -> dict:
    since = timezone.now() - timedelta(days=max(1, min(days, 365)))
    activity: list[dict] = []
    assignments: list[dict] = []
    collections: list[dict] = []
    for node_key, provider in providers().items():
        if not _enabled(node_key):
            continue
        projection = provider(user=user, person=person, since=since)
        activity.extend(projection.get("activity", []))
        assignments.extend(projection.get("assignments", []))
        collections.extend(projection.get("collections", []))
    activity.sort(key=lambda row: row.get("occurred_at") or "", reverse=True)
    assignments.sort(key=lambda row: (row.get("due_at") is None, row.get("due_at") or "", row.get("title") or ""))
    activity = activity[:100]
    keys = [row["key"] for row in activity]
    reactions = CornerReaction.objects.filter(activity_key__in=keys).select_related("reactor")
    grouped: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    reactor_id = getattr(person_for_user(user), "id", None)
    for reaction in reactions:
        grouped[reaction.activity_key][reaction.emoji].append({
            "person_id": reaction.reactor_id,
            "name": reaction.reactor.name,
            "mine": reaction.reactor_id == reactor_id,
        })
    for row in activity:
        row["reactions"] = [
            {"emoji": emoji, "count": len(people), "people": people,
             "mine": any(person_row["mine"] for person_row in people)}
            for emoji, people in grouped[row["key"]].items()
        ]
    return {
        "person": {
            "id": person.id, "display_name": person.display_name, "preferred_name": person.preferred_name,
            "name": person.name, "avatar": person.avatar, "colour": person.colour,
            "profile_type": person.profile_type, "is_me": reactor_id == person.id,
        },
        "summary": {"activity_count": len(activity), "assignment_count": len(assignments),
                    "collection_count": len(collections)},
        "activity": activity, "assignments": assignments, "collections": collections,
    }


def find_activity(user, person: Person, activity_key: str) -> dict | None:
    return next((row for row in build_corner(user, person)["activity"] if row["key"] == activity_key), None)
