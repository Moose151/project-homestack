"""notifications selectors — read-only queries (scoped to the requesting user)."""
from __future__ import annotations

from apps.notifications.models import Notification


def list_for_user(user, *, unread_only: bool = False, limit: int = 50) -> list[Notification]:
    qs = Notification.objects.filter(recipient_user=user)
    if unread_only:
        qs = qs.filter(is_read=False)
    return list(qs[:limit])


def unread_count(user) -> int:
    return Notification.objects.filter(recipient_user=user, is_read=False).count()


def get_for_user(user, pk: int) -> Notification | None:
    return Notification.objects.filter(recipient_user=user, pk=pk).first()
