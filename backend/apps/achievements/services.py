"""achievements services — awarding badges and maintaining per-person counters.

All writes go through here. `award_badge` is idempotent and publishes `achievements.badge_earned`
so notifications / the kiosk can react (D4). Counters are the app's own aggregates, updated by
the event handlers.
"""
from __future__ import annotations

from django.db import transaction
from django.db.models import F

from apps.achievements import events
from apps.achievements.models import AchievementCounter, Badge, PersonBadge
from apps.core.models import get_active_household


@transaction.atomic
def award_badge(person_id: int, code: str, *, source: str = "") -> tuple[PersonBadge | None, bool]:
    """Award a badge to a person if they don't already have it. Returns (person_badge, created)."""
    badge = Badge.objects.filter(code=code).first()
    if badge is None:
        return None, False
    existing = PersonBadge.all_objects.filter(person_id=person_id, badge=badge).first()
    if existing is not None:
        return existing, False
    pb = PersonBadge(
        household=get_active_household(),
        person_id=person_id,
        badge=badge,
        source=source or badge.source,
    )
    pb.save()
    events.badge_earned(person_id, pb.household_id, badge.code, badge.name, badge.icon)
    return pb, True


def bump_counter(person_id: int, key: str, delta: int = 1) -> int:
    """Atomically add ``delta`` to a person's counter and return the new value."""
    counter, _ = AchievementCounter.all_objects.get_or_create(
        person_id=person_id, key=key,
        defaults={"household": get_active_household(), "value": 0},
    )
    AchievementCounter.all_objects.filter(pk=counter.pk).update(value=F("value") + delta)
    counter.refresh_from_db(fields=["value"])
    return counter.value


def raise_counter_to(person_id: int, key: str, value: int) -> int:
    """Set a counter to ``max(current, value)`` — for metrics that report a current level
    (e.g. a routine streak) rather than an increment. Returns the stored value."""
    counter, _ = AchievementCounter.all_objects.get_or_create(
        person_id=person_id, key=key,
        defaults={"household": get_active_household(), "value": 0},
    )
    if value > counter.value:
        counter.value = value
        counter.save(update_fields=["value", "updated_at"])
    return counter.value
