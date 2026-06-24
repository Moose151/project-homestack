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

    qs = HouseholdHubWidget.objects.filter(is_enabled=True).select_related("widget")
    if kiosk_mode:
        qs = qs.filter(widget__supports_kiosk=True)

    # Check user-level overrides (disable only — no enable above household default)
    hidden_keys: set[str] = set()
    from apps.hub.models import UserHubWidget
    for uw in UserHubWidget.objects.filter(user=user, is_enabled=False).select_related("widget"):
        hidden_keys.add(uw.widget.key)

    widgets = []
    for hw in qs.order_by("display_order"):
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
