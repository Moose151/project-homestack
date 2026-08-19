"""Atlas event-bus subscribers (D4) — connected from AtlasConfig.ready().

Atlas keeps one To-do list per active Person (D19 §D). When a Person goes, that list has to go
with them, but their outstanding jobs are still real household work. Handling it here — off
`people`'s domain event rather than an import in `people.services` — keeps the dependency
pointing the way the architecture requires: `people` publishes that someone was removed and
knows nothing about lists.
"""
from __future__ import annotations

from django.utils import timezone

from apps.events.bus import subscribe


def _on_person_deleted(sender, *, payload, **kwargs) -> None:
    """Rehome a deleted Person's To-dos onto the Household list, then retire their list.

    Moving the items first is the point: a personal list is hidden the moment its owner is
    deleted (see selectors.list_todo_lists), so anything left on it would stay in the Hub's
    To-do widget and the Today view while being unreachable from the To-dos tab.
    """
    from apps.atlas.models import AtlasList, AtlasListItem

    person_id = payload.get("person_id")
    household_id = payload.get("household_id")
    if person_id is None:
        return

    household_list = (
        AtlasList.objects.filter(
            household_id=household_id, list_type=AtlasList.ListType.TODO,
            owner_person__isnull=True,
        )
        .order_by("created_at", "id")
        .first()
    )
    personal_lists = list(
        AtlasList.objects.filter(
            household_id=household_id, list_type=AtlasList.ListType.TODO,
            owner_person_id=person_id,
        )
    )
    if not personal_lists:
        return
    if household_list is None:
        household_list = AtlasList.objects.create(
            household_id=household_id, title="Household", list_type=AtlasList.ListType.TODO,
        )

    now = timezone.now()
    for personal in personal_lists:
        AtlasListItem.objects.filter(atlas_list=personal).update(
            atlas_list=household_list, updated_at=now,
        )
        personal.soft_delete()


def connect() -> None:
    subscribe("people.person_deleted", _on_person_deleted)
