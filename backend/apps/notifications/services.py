"""notifications services — create and manage per-user notifications.

Nodes call `create_notification` / `notify_person` directly (shared infrastructure pattern).
`notify_person` resolves a person to their linked user and no-ops if the person has no login
(e.g. a young child with kiosk-only access still has a linked user; a person with none is
simply skipped).
"""
from __future__ import annotations

from apps.core.models import get_active_household
from apps.notifications.models import Notification


def create_notification(
    recipient_user, *, title: str, message: str,
    level: str = Notification.Level.INFO, source_node: str = "", action_url: str = "",
) -> Notification | None:
    if recipient_user is None:
        return None
    note = Notification(
        household=get_active_household(),
        recipient_user=recipient_user,
        title=title,
        message=message,
        level=level,
        source_node=source_node,
        action_url=action_url,
    )
    note.save()
    return note


def notify_person(person, **kwargs) -> Notification | None:
    """Notify the user linked to a person; no-op if the person has no login."""
    if person is None:
        return None
    user = getattr(person, "linked_user", None)
    if user is None:
        return None
    return create_notification(user, **kwargs)


def notify_person_id(person_id: int | None, **kwargs) -> Notification | None:
    if not person_id:
        return None
    from apps.people.models import Person
    person = Person.all_objects.filter(pk=person_id).first()
    return notify_person(person, **kwargs)


def mark_read(notification: Notification) -> Notification:
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read", "updated_at"])
    return notification


def mark_all_read(user) -> int:
    return Notification.objects.filter(recipient_user=user, is_read=False).update(is_read=True)
