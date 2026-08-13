"""notifications selectors — read-only queries (scoped to the requesting user)."""
from __future__ import annotations

from apps.notifications.models import (
    MINE_ONLY_CATEGORIES,
    Notification,
    NotificationCategory,
    NotificationPreference,
    PUSH_OFF_BY_DEFAULT,
    PushDevice,
)


def list_for_user(user, *, unread_only: bool = False, limit: int = 50) -> list[Notification]:
    qs = Notification.objects.filter(recipient_user=user)
    if unread_only:
        qs = qs.filter(is_read=False)
    return list(qs[:limit])


def unread_count(user) -> int:
    return Notification.objects.filter(recipient_user=user, is_read=False).count()


def get_for_user(user, pk: int) -> Notification | None:
    return Notification.objects.filter(recipient_user=user, pk=pk).first()


def list_preferences_for_user(user) -> list[dict]:
    """Every category, always — saved rows override the docs/32 §3 defaults, never omit one."""
    saved = {row.category: row for row in NotificationPreference.objects.filter(user=user)}
    rows = []
    for value, label in NotificationCategory.choices:
        row = saved.get(value)
        rows.append({
            "category": value,
            "label": label,
            "in_app_enabled": row.in_app_enabled if row else True,
            "push_enabled": row.push_enabled if row else value not in PUSH_OFF_BY_DEFAULT,
            "mine_only": row.mine_only if row else False,
            "supports_mine_only": value in MINE_ONLY_CATEGORIES,
        })
    return rows


def list_devices(user) -> list[PushDevice]:
    return list(PushDevice.objects.filter(user=user, is_active=True))


def get_device(user, pk: int) -> PushDevice | None:
    return PushDevice.objects.filter(user=user, pk=pk).first()


def get_device_by_endpoint(user, endpoint: str) -> PushDevice | None:
    """Resolve only the caller's active subscription for current-device UI labelling."""
    return PushDevice.objects.filter(user=user, endpoint=endpoint, is_active=True).first()


def list_devices_by_user() -> list[dict]:
    """Every active push device in the household, grouped by owning User.

    Powers the admin overview only (docs/32 §7) — the self-service device endpoints stay
    strictly current-User scoped. Users with no devices are omitted: the screen answers
    "who is set up for push", so an empty group would be noise.
    """
    devices = list(
        PushDevice.objects.filter(is_active=True)
        .select_related("user")
        .order_by("user__display_name", "user_id", "label")
    )
    groups: dict[int, dict] = {}
    for device in devices:
        group = groups.setdefault(
            device.user_id,
            {
                "user_id": device.user_id,
                "user_display_name": device.user.display_name,
                "user_role": device.user.role,
                "devices": [],
            },
        )
        group["devices"].append(device)
    return list(groups.values())
