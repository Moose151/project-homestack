"""notifications services — create and manage per-user notifications.

Nodes call `create_notification` / `notify_person` directly (shared infrastructure pattern).
`notify_person` resolves a person to their linked user and no-ops if the person has no login
(e.g. a young child with kiosk-only access still has a linked user; a person with none is
simply skipped).
"""
from __future__ import annotations

from apps.core.models import get_active_household
from apps.notifications.models import (
    Notification,
    NotificationCategory,
    NotificationPreference,
    UserNotificationSettings,
)


def create_notification(
    recipient_user, *, title: str, message: str,
    level: str = Notification.Level.INFO, source_node: str = "", action_url: str = "",
    category: str = "",
) -> Notification | None:
    """Create the in-app notification, gated by the recipient's preference for `category`.

    `category=""` (the default) bypasses the gate entirely — every call site written before
    docs/32_Core_Notifications_and_Push.md existed keeps behaving exactly as it always has.
    A real category checks NotificationPreference.in_app_enabled; a missing row defaults to
    enabled (docs/32 §3/§5), so setting a category is additive, never silently suppressive,
    until the household actually turns something off.
    """
    if recipient_user is None:
        return None
    if category and not _in_app_enabled(recipient_user, category):
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


def _in_app_enabled(recipient_user, category: str) -> bool:
    pref = NotificationPreference.objects.filter(user=recipient_user, category=category).first()
    return pref.in_app_enabled if pref else True


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


def set_preference(
    user, *, category: str, in_app_enabled: bool, push_enabled: bool, mine_only: bool = False,
) -> NotificationPreference:
    if category not in NotificationCategory.values:
        raise ValueError("Unknown notification category.")
    pref, _ = NotificationPreference.objects.update_or_create(
        user=user, category=category,
        defaults={
            "in_app_enabled": in_app_enabled,
            "push_enabled": push_enabled,
            "mine_only": mine_only,
            "household": get_active_household(),
            "created_by": user,
            "updated_by": user,
        },
    )
    return pref


def set_preferences(user, rows: list[dict]) -> list[NotificationPreference]:
    return [
        set_preference(
            user,
            category=row["category"],
            in_app_enabled=row.get("in_app_enabled", True),
            push_enabled=row.get("push_enabled", True),
            mine_only=row.get("mine_only", False),
        )
        for row in rows
    ]


def get_or_create_settings(user) -> UserNotificationSettings:
    settings_obj, _ = UserNotificationSettings.objects.get_or_create(
        user=user, defaults={"household": get_active_household(), "created_by": user, "updated_by": user},
    )
    return settings_obj


def update_settings(user, **data) -> UserNotificationSettings:
    settings_obj = get_or_create_settings(user)
    for field in {"quiet_start", "quiet_end", "morning_time"}:
        if field in data:
            setattr(settings_obj, field, data[field])
    settings_obj.updated_by = user
    settings_obj.save()
    return settings_obj
