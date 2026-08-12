"""Web Push delivery — docs/32_Core_Notifications_and_Push.md §10.

Kept separate from services.py so the pywebpush/VAPID mechanics don't clutter the plain in-app
notification path. Delivery is always best-effort (docs/32 §10: "the in-app notification centre
remains the source of truth") — nothing here may raise into the caller, which already has its
in-app row by the time this runs.
"""
from __future__ import annotations

import json
import logging
from datetime import time as time_cls
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings as django_settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from apps.core.models import get_active_household
from apps.notifications import device_naming
from apps.notifications.models import (
    PUSH_OFF_BY_DEFAULT,
    NotificationPreference,
    PushDevice,
    UserNotificationSettings,
)

logger = logging.getLogger(__name__)


def vapid_configured() -> bool:
    return bool(django_settings.VAPID_PUBLIC_KEY and django_settings.VAPID_PRIVATE_KEY)


def _household_timezone(user) -> ZoneInfo:
    name = getattr(getattr(user, "household", None), "timezone", "") or "UTC"
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _push_enabled(recipient_user, category: str) -> bool:
    pref = NotificationPreference.objects.filter(user=recipient_user, category=category).first()
    if pref:
        return pref.push_enabled
    return category not in PUSH_OFF_BY_DEFAULT


def _is_sensitive_source(source_node: str) -> bool:
    """Never push for a re-auth-gated node (docs/32 §10) — Solace/Health stay in-app-only,
    regardless of category, even if a future call site mistakenly tags one with a category."""
    if not source_node:
        return False
    from apps.nodes.models import HouseholdNode

    return HouseholdNode.objects.filter(
        node__key=source_node, requires_reauthentication=True,
    ).exists()


def _in_quiet_hours(user) -> bool:
    try:
        row = user.notification_settings
    except ObjectDoesNotExist:
        return False
    if not row.quiet_start or not row.quiet_end:
        return False
    now_local = timezone.localtime(timezone.now(), _household_timezone(user)).time()
    start, end = row.quiet_start, row.quiet_end
    if start <= end:
        return start <= now_local <= end
    return now_local >= start or now_local <= end  # overnight wrap, e.g. 22:00-07:00


def send_push_to_user(
    user, *, category: str, source_node: str, title: str, message: str, action_url: str = "",
) -> None:
    if not vapid_configured():
        return
    if _is_sensitive_source(source_node):
        return
    if not _push_enabled(user, category):
        return
    if _in_quiet_hours(user):
        return
    devices = list(PushDevice.objects.filter(user=user, is_active=True))
    if not devices:
        return
    payload = json.dumps({"title": title, "body": message, "url": action_url})
    for device in devices:
        try:
            _send_to_device(device, payload)
        except Exception:  # noqa: BLE001 — delivery is best-effort, never break the caller
            logger.warning("Push delivery failed for device %s", device.id, exc_info=True)


def send_test_push(device: PushDevice) -> bool:
    """Explicit user action from the device list — bypasses category/quiet-hours checks."""
    if not vapid_configured():
        raise ValueError("VAPID keys are not configured on this server.")
    payload = json.dumps({
        "title": "Test notification", "body": "Push is working on this device.", "url": "/",
    })
    return _send_to_device(device, payload)


def _send_to_device(device: PushDevice, payload: str) -> bool:
    from pywebpush import WebPushException, webpush

    try:
        webpush(
            subscription_info={
                "endpoint": device.endpoint,
                "keys": {"p256dh": device.p256dh, "auth": device.auth},
            },
            data=payload,
            vapid_private_key=django_settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": django_settings.VAPID_SUBJECT},
        )
        return True
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        if status in (404, 410):
            device.is_active = False
            device.save(update_fields=["is_active", "updated_at"])
        return False


def register_device(user, *, endpoint: str, p256dh: str, auth: str, label: str = "", user_agent: str = "") -> PushDevice:
    """Create or refresh the subscription for `endpoint`.

    An explicit `label` from the caller wins and counts as a custom name. Otherwise the label is
    generated from the User-Agent — but only for a device that has never been renamed, so
    re-enabling push in the same browser refreshes the keys and technical detail without
    stomping on "Nick's Laptop".
    """
    browser, platform, generated = device_naming.describe(user_agent)
    existing = PushDevice.all_objects.filter(endpoint=endpoint).first()
    defaults = {
        "user": user, "p256dh": p256dh, "auth": auth,
        "browser": browser, "platform": platform,
        "user_agent": user_agent, "is_active": True,
        "household": get_active_household(), "created_by": user, "updated_by": user,
    }
    if label:
        defaults["label"] = label
        defaults["label_is_custom"] = True
    elif not (existing and existing.label_is_custom):
        defaults["label"] = generated
    device, _ = PushDevice.objects.update_or_create(endpoint=endpoint, defaults=defaults)
    return device


def rename_device(user, device_id: int, label: str) -> PushDevice | None:
    """Rename the caller's own device. Returns None if it isn't theirs (or doesn't exist).

    A blank label deliberately resets to the generated name rather than leaving the device
    nameless in the list.
    """
    device = PushDevice.objects.filter(user=user, pk=device_id).first()
    if device is None:
        return None
    label = label.strip()
    device.label = label or device_naming.default_label(device.browser, device.platform)
    device.label_is_custom = bool(label)
    device.updated_by = user
    device.save(update_fields=["label", "label_is_custom", "updated_by", "updated_at"])
    return device


def unregister_device(user, device_id: int) -> bool:
    deleted, _ = PushDevice.objects.filter(user=user, pk=device_id).delete()
    return bool(deleted)
