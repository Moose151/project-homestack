from __future__ import annotations

from django.db import transaction
from urllib.parse import quote

from apps.core.models import get_active_household
from apps.notifications.services import notify_bundled
from apps.people import corners
from apps.people.models import CornerReaction, Person
from apps.people.selectors import person_for_user

ALLOWED_REACTIONS = {"❤️", "👍", "🎉", "💪", "👏"}


@transaction.atomic
def toggle_reaction(*, acting_user, owner: Person, activity_key: str, emoji: str) -> bool:
    if emoji not in ALLOWED_REACTIONS:
        raise ValueError("Choose one of the available reactions.")
    reactor = person_for_user(acting_user)
    if reactor is None:
        raise ValueError("Your login must be linked to a household member to react.")
    activity = corners.find_activity(acting_user, owner, activity_key)
    if activity is None:
        raise ValueError("That activity is no longer available.")
    existing = CornerReaction.objects.filter(
        activity_key=activity_key, reactor=reactor, emoji=emoji
    ).first()
    if existing:
        existing.soft_delete()
        return False
    previous = CornerReaction.all_objects.filter(
        household=get_active_household(), activity_key=activity_key, reactor=reactor, emoji=emoji,
        deleted_at__isnull=False,
    ).first()
    if previous:
        previous.activity_owner = owner
        previous.updated_by = acting_user
        previous.deleted_at = None
        previous.save(update_fields=["activity_owner", "updated_by", "deleted_at", "updated_at"])
        if owner.id != reactor.id:
            _notify_reaction(owner=owner, activity_key=activity_key, activity=activity)
        return True
    CornerReaction.objects.create(
        household=get_active_household(), activity_key=activity_key, activity_owner=owner,
        reactor=reactor, emoji=emoji, created_by=acting_user, updated_by=acting_user,
    )
    if owner.id != reactor.id:
        _notify_reaction(owner=owner, activity_key=activity_key, activity=activity)
    return True


def _notify_reaction(*, owner: Person, activity_key: str, activity: dict) -> None:
    """Bundle unread reaction bursts for one activity into a single notification.

    docs/32_Core_Notifications_and_Push.md §6 — this was the original pattern `notify_bundled`
    generalises; kept here as the reference caller rather than duplicating the logic.
    """
    if owner.linked_user_id is None:
        return
    names = list(CornerReaction.objects.filter(
        activity_key=activity_key,
    ).exclude(reactor=owner).values_list("reactor__display_name", flat=True).distinct())
    if not names:
        return
    title = f"{names[0]} reacted to your activity" if len(names) == 1 else f"{names[0]} and {len(names) - 1} other{'s' if len(names) > 2 else ''} reacted"
    action_url = f"/corners/{owner.id}?tab=activity&activity={quote(activity_key, safe='')}"
    notify_bundled(
        owner.linked_user, category="corners", source_node="corners",
        title=title, message=f"Encouragement on {activity['title']}.", action_url=action_url,
    )
