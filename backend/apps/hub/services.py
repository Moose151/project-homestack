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
    from apps.atlas.selectors import list_open_items, list_reminders
    from apps.atlas.serializers import AtlasListItemSerializer, AtlasReminderSerializer

    qs = HouseholdHubWidget.objects.filter(
        household=user.household, is_enabled=True
    ).select_related("widget")
    if kiosk_mode:
        qs = qs.filter(widget__supports_kiosk=True)

    # A widget belonging to a disabled stack (node) must not appear — disabling a stack
    # hides its Hub widgets too. Core widgets (source_node is null) are always allowed.
    from apps.nodes.models import HouseholdNode
    enabled_node_ids = set(
        HouseholdNode.objects.filter(household=user.household, is_enabled=True)
        .values_list("node_id", flat=True)
    )

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
        # Skip widgets whose stack is disabled for this household.
        if hw.widget.source_node_id and hw.widget.source_node_id not in enabled_node_ids:
            continue

        content: list = []
        meta: dict = {}

        if key == "notifications_summary":
            from apps.notifications.selectors import list_for_user, unread_count
            from apps.notifications.serializers import NotificationSerializer
            recent = list_for_user(user, unread_only=True, limit=6)
            content = NotificationSerializer(recent, many=True).data
            meta = {"unread_count": unread_count(user)}

        elif key in ("quick_add", "daily_quote"):
            # Client-rendered ambient/utility widgets — own no domain data (Hub spec §6).
            content = []

        elif key == "atlas_todos":
            content = AtlasListItemSerializer(list_open_items(user, limit=20), many=True).data

        elif key == "atlas_reminders":
            week_ahead = timezone.now() + timezone.timedelta(days=7)
            reminders = list_reminders(user, upcoming_only=True)
            reminders = [r for r in reminders if r.due_at and r.due_at <= week_ahead][:10]
            content = AtlasReminderSerializer(reminders, many=True).data

        elif key == "calendar_upcoming":
            from apps.scheduling.selectors import list_events
            from apps.scheduling.serializers import CalendarEventSerializer
            upcoming = list_events(user, upcoming_only=True)[:8]
            content = CalendarEventSerializer(upcoming, many=True).data

        elif key.startswith("meridian_"):
            content = _meridian_widget_content(key, user)

        elif key.startswith("education_"):
            content = _education_widget_content(key, user)

        elif key.startswith("wiki_"):
            content = _wiki_widget_content(key, user)

        widgets.append({
            "key": key,
            "name": hw.widget.name,
            "size": hw.size,
            "supports_kiosk": hw.widget.supports_kiosk,
            "items": content,
            "meta": meta,
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


def _education_widget_content(key: str, user) -> list:
    """Assemble content for an Education hub widget (Node Spec 8), permission-filtered."""
    from apps.education import selectors as e
    from apps.education.serializers import (
        EducationAssessmentSerializer,
        EducationClassSessionSerializer,
        EducationEventSerializer,
    )

    if key == "education_deadlines":
        assessments = e.list_assessments(user, upcoming_only=True, open_only=True, limit=10)
        return EducationAssessmentSerializer(assessments, many=True).data

    if key == "education_classes":
        sessions = e.list_class_sessions(user)[:10]
        return EducationClassSessionSerializer(sessions, many=True).data

    if key == "education_events":
        events = e.list_events(user, upcoming_only=True, limit=10)
        return EducationEventSerializer(events, many=True).data

    return []


def _wiki_widget_content(key: str, user) -> list:
    """Assemble content for a Home Wiki hub widget (Node Spec 8), permission-filtered."""
    from apps.home_wiki import selectors as w
    from apps.home_wiki.serializers import WikiPageSerializer

    if key == "wiki_favourites":
        pages = w.list_pages(user, favourites_only=True, limit=8)
        return WikiPageSerializer(pages, many=True).data

    if key == "wiki_emergency":
        pages = w.list_pages(user, emergency_only=True, limit=8)
        return WikiPageSerializer(pages, many=True).data

    if key == "wiki_recent":
        pages = w.list_pages(user, order_by_updated=True, limit=6)
        return WikiPageSerializer(pages, many=True).data

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
