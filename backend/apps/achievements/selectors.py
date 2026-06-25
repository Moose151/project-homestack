"""achievements selectors — read-only queries."""
from __future__ import annotations

from apps.achievements.models import Badge, PersonBadge


def all_badges() -> list[Badge]:
    return list(Badge.objects.all())


def person_badges(person_id: int) -> list[PersonBadge]:
    return list(PersonBadge.objects.filter(person_id=person_id).select_related("badge"))


def badges_by_person() -> dict[int, list[PersonBadge]]:
    """All earned badges grouped by person_id — drives the Hub badge widget."""
    out: dict[int, list[PersonBadge]] = {}
    for pb in PersonBadge.objects.select_related("badge"):
        out.setdefault(pb.person_id, []).append(pb)
    return out
