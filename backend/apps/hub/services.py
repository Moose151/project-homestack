"""hub services — assemble widget content for the hub and kiosk views.

Hub imports from atlas.selectors (not atlas.models) to assemble widget data.
This is a direct dependency that will be decoupled via a widget provider registry
in Milestone 2 when more nodes contribute hub widgets.
"""
from __future__ import annotations

from django.utils import timezone

from apps.hub.models import HouseholdHubWidget


def get_hub_widgets(user, *, kiosk_mode: bool = False) -> list[dict]:
    """Return assembled hub widget content for the authenticated user.

    kiosk_mode=True restricts to widgets where supports_kiosk=True.
    """
    from apps.atlas.selectors import list_items_for_list, list_reminders, list_atlas_lists
    from apps.atlas.serializers import AtlasListItemSerializer, AtlasReminderSerializer

    qs = HouseholdHubWidget.objects.filter(
        household=user.household, is_enabled=True
    ).select_related("widget")
    if kiosk_mode:
        qs = qs.filter(widget__supports_kiosk=True)

    # Per-user overrides: hide widgets, and reorder (user order wins over household order).
    from apps.hub.models import UserHubWidget
    hidden_keys: set[str] = set()
    user_order: dict[str, int] = {}
    for uw in UserHubWidget.objects.filter(user=user).select_related("widget"):
        if not uw.is_enabled:
            hidden_keys.add(uw.widget.key)
        else:
            user_order[uw.widget.key] = uw.display_order

    ordered = sorted(
        qs, key=lambda hw: (user_order.get(hw.widget.key, hw.display_order), hw.widget.key)
    )

    widgets = []
    for hw in ordered:
        key = hw.widget.key
        if key in hidden_keys:
            continue

        content: list = []

        if key == "atlas_todos":
            from apps.atlas.models import AtlasListItem
            items = list(
                AtlasListItem.objects.filter(
                    completed_at__isnull=True,
                    deleted_at__isnull=True,
                ).order_by("atlas_list__title", "position")[:20]
            )
            content = AtlasListItemSerializer(items, many=True).data

        elif key == "atlas_reminders":
            week_ahead = timezone.now() + timezone.timedelta(days=7)
            reminders = list_reminders(user, upcoming_only=True)
            reminders = [r for r in reminders if r.due_at and r.due_at <= week_ahead][:10]
            content = AtlasReminderSerializer(reminders, many=True).data

        elif key.startswith("meridian_"):
            content = _meridian_widget_content(key, user)

        widgets.append({
            "key": key,
            "name": hw.widget.name,
            "size": hw.size,
            "supports_kiosk": hw.widget.supports_kiosk,
            "items": content,
        })

    return widgets


def _meridian_widget_content(key: str, user) -> list:
    """Assemble content for a Meridian hub widget (Node Spec 8).

    Mirrors the inline Atlas pattern above. A widget-provider registry is the natural
    next refactor once a third node contributes widgets, but is deferred to keep this
    change reviewable and consistent with the established Atlas approach.
    """
    from apps.meridian import selectors as m
    from apps.meridian.serializers import (
        MeridianRewardRequestSerializer,
        MeridianTaskSerializer,
        PointsSummarySerializer,
    )

    person = getattr(user, "person_profile", None)
    person_id = person.id if person else None

    if key == "meridian_my_tasks":
        tasks = m.list_tasks(user, status="available")
        if person_id:
            tasks = [t for t in tasks if t.assigned_to_person_id in (None, person_id)]
        return MeridianTaskSerializer(tasks[:20], many=True).data

    if key == "meridian_hot_tasks":
        return MeridianTaskSerializer(m.list_tasks(user, hot_only=True)[:20], many=True).data

    if key == "meridian_points":
        return PointsSummarySerializer(m.points_summary(), many=True).data

    if key == "meridian_pending_approvals":
        return MeridianTaskSerializer(m.list_pending_tasks(user)[:20], many=True).data

    if key == "meridian_reward_requests":
        return MeridianRewardRequestSerializer(
            m.list_reward_requests(status="pending")[:20], many=True
        ).data

    return []


class HubError(Exception):
    """Domain error for hub configuration (e.g. unknown widget key)."""


def _get_widget(key: str):
    from apps.hub.models import HubWidget
    widget = HubWidget.objects.filter(key=key).first()
    if widget is None:
        raise HubError("Unknown widget.")
    return widget


def set_household_widget(user, key: str, *, is_enabled=None, display_order=None, size=None):
    """Configure a widget for the whole household (admin/manager). Upserts the row."""
    from apps.hub.models import HouseholdHubWidget
    widget = _get_widget(key)
    config, _ = HouseholdHubWidget.objects.get_or_create(
        household=user.household, widget=widget,
        defaults={"display_order": widget.display_order},
    )
    if is_enabled is not None:
        config.is_enabled = is_enabled
    if display_order is not None:
        config.display_order = display_order
    if size is not None:
        if size not in {"small", "medium", "large"}:
            raise HubError("Invalid size.")
        config.size = size
    config.save()
    return config


def set_user_widget(user, key: str, *, is_enabled=None, display_order=None):
    """Per-user override — hide/show or reorder a widget on this user's own Hub. Upserts."""
    from apps.hub.models import UserHubWidget
    widget = _get_widget(key)
    config, _ = UserHubWidget.objects.get_or_create(user=user, widget=widget)
    if is_enabled is not None:
        config.is_enabled = is_enabled
    if display_order is not None:
        config.display_order = display_order
    config.save()
    return config
