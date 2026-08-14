"""hub services — assemble widget content for the hub and kiosk views.

Hub imports from atlas.selectors (not atlas.models) to assemble widget data.
This is a direct dependency that will be decoupled via a widget provider registry
in Milestone 2 when more nodes contribute hub widgets.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta

from django.db import transaction
from django.utils import timezone

from apps.hub.models import HouseholdHubWidget

# How far ahead the unified "Upcoming" widget fetches. The client clips this to the
# horizon the reader picked, so one request serves every horizon without a round trip.
UPCOMING_MAX_DAYS = 62

# How far back an unfinished dated record still counts as "overdue" rather than history.
UPCOMING_OVERDUE_GRACE_DAYS = 30

# Source record types that mean "this is due by then". A missed one still needs attention,
# so it survives past its date. Point-in-time records (appointments, classes, one-off
# events) are history once they pass and are dropped instead.
UPCOMING_DUE_RECORD_TYPES = frozenset({
    "AtlasReminder",
    "Bill",
    "BillOccurrence",
    "EducationAssessment",
    "MaintenanceTask",
    "MeridianTask",
    "PetTreatment",
    "PlannedPurchase",
})


def get_hub_widgets(user, *, kiosk_mode: bool = False, sensitive_unlocked: bool = False) -> list[dict]:
    """Return assembled hub widget content for the authenticated user.

    kiosk_mode=True restricts to widgets where supports_kiosk=True.

    A widget with nothing to show is dropped from the response rather than rendered as an
    empty card, so the Hub only carries things that actually need attention. Ambient
    widgets opt out of that with ``HubWidget.always_visible``.
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
    from apps.nodes.permissions import can_view_node
    enabled_node_ids = {
        household_node.node_id
        for household_node in HouseholdNode.objects.filter(
            household=user.household, is_enabled=True
        ).select_related("node")
        if can_view_node(user, household_node.node.key)
    }

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

        elif key == "countdown":
            content = []
            meta = dict(hw.settings_json or {})
            # Date-only settings from older releases deliberately become noon, not midnight.
            meta.setdefault("target_time", "12:00")
            if meta.get("target_date"):
                from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
                try:
                    target = datetime.combine(
                        datetime.fromisoformat(meta["target_date"]).date(),
                        time.fromisoformat(meta["target_time"]),
                        tzinfo=ZoneInfo(user.household.timezone),
                    )
                    meta["target_at"] = target.isoformat()
                except (TypeError, ValueError, ZoneInfoNotFoundError):
                    pass

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

        elif key == "upcoming":
            content, meta = _upcoming_widget_content(
                user, sensitive_unlocked=sensitive_unlocked
            )

        elif key.startswith("meridian_"):
            content = _meridian_widget_content(key, user)

        elif key.startswith("education_"):
            content = _education_widget_content(key, user)

        elif key.startswith("wiki_"):
            content = _wiki_widget_content(key, user)

        elif key.startswith("pets_"):
            content = _pets_widget_content(key, user)

        elif key.startswith("homestead_"):
            content = _homestead_widget_content(key, user)

        elif key.startswith("solace_"):
            content = _solace_widget_content(key, user) if sensitive_unlocked else []

        elif key.startswith("fitness_"):
            content = _fitness_widget_content(key, user)

        # An empty card is noise on a dashboard: it takes a grid slot to say "nothing here".
        # Drop it unless the widget is ambient (clock/quick add/countdown), which has no
        # content by design and is still worth showing.
        if not content and not hw.widget.always_visible:
            continue

        widgets.append({
            "key": key,
            "name": hw.widget.name,
            "size": hw.size,
            "supports_kiosk": hw.widget.supports_kiosk,
            "items": content,
            "meta": meta,
        })

    return widgets


def _upcoming_widget_content(user, *, sensitive_unlocked: bool) -> tuple[list, dict]:
    """One card for everything dated, instead of a permanent card per node.

    The Calendar already owns every dated household record (D7) — nodes sync into it via
    the scheduling helper and never write it directly — so aggregating calendar events
    covers Atlas, Pets, Education, Homestead, Meridian and Solace in a single pass, with
    no double counting and with visibility/sensitivity filtering already applied (D10).

    Returns the full ``UPCOMING_MAX_DAYS`` window plus the horizon boundaries; the client
    clips to the horizon the reader chose, so switching horizon costs no round trip.
    """
    from apps.scheduling.selectors import list_events
    from apps.scheduling.serializers import CalendarEventSerializer

    today = timezone.localdate()
    start_of_today = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)

    events = list_events(
        user,
        start=start_of_today - timedelta(days=UPCOMING_OVERDUE_GRACE_DAYS),
        end=start_of_today + timedelta(days=UPCOMING_MAX_DAYS),
        sensitive_unlocked=sensitive_unlocked,
    )
    relevant = [
        event
        for event in events
        if event.start_at >= start_of_today
        or event.source_record_type in UPCOMING_DUE_RECORD_TYPES
    ]

    meta = {
        "horizons": _upcoming_horizons(user, today, sensitive_unlocked=sensitive_unlocked),
        "default_horizon": "week",
        "window_days": UPCOMING_MAX_DAYS,
    }
    return CalendarEventSerializer(relevant, many=True).data, meta


def _upcoming_horizons(user, today, *, sensitive_unlocked: bool) -> list[dict]:
    """Selectable ranges for the Upcoming widget, narrowest first.

    Labels state the actual window rather than "this week"/"this month" so a Friday reader
    is not shown a two-day list under a label that promises a week.
    """
    horizons = [
        {"key": "week", "label": "Next 7 days", "until": (today + timedelta(days=7)).isoformat()},
    ]
    cycle_end = _pay_cycle_end(user) if sensitive_unlocked else None
    if cycle_end and cycle_end > today:
        horizons.append(
            {"key": "cycle", "label": "This pay cycle", "until": cycle_end.isoformat()}
        )
    horizons.append(
        {"key": "month", "label": "Next 30 days", "until": (today + timedelta(days=30)).isoformat()}
    )
    return horizons


def _pay_cycle_end(user):
    """End of the current Solace pay cycle, or None when Money is unavailable/unconfigured.

    A horizon is a display convenience — a household with no paydays configured yet must
    still get a working Hub, so a failure here drops the horizon rather than the widget.
    """
    from datetime import date

    from apps.permissions.resolver import resolve_permission

    if not resolve_permission(user, "view", "solace"):
        return None
    try:
        from apps.solace.selectors import get_pay_cycle_plan
        return date.fromisoformat(get_pay_cycle_plan(user)["cycle_end"])
    except Exception:  # noqa: BLE001 — unconfigured Solace must not break the Hub
        return None


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
            tasks = [
                t for t in tasks
                if not t.assigned_to_people.exists()
                or t.assigned_to_people.filter(id=person_id).exists()
            ]
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


def _pets_widget_content(key: str, user) -> list:
    """Assemble content for a Pets hub widget (Node Spec 8), permission-filtered."""
    from apps.pets import selectors as p
    from apps.pets.serializers import PetAppointmentSerializer, PetTreatmentSerializer

    if key == "pets_reminders":
        treatments = p.list_treatments(user, due_only=True, limit=8)
        return PetTreatmentSerializer(treatments, many=True).data

    if key == "pets_appointments":
        appointments = p.list_appointments(user, upcoming_only=True, limit=8)
        return PetAppointmentSerializer(appointments, many=True).data

    return []


def _fitness_widget_content(key: str, user) -> list:
    """Recent household training, filtered through session visibility."""
    from apps.fitness import selectors as fitness
    from apps.fitness.serializers import WorkoutSessionSerializer

    if key == "fitness_recent":
        sessions = fitness.list_sessions(user, status="completed", limit=6)
        return WorkoutSessionSerializer(sessions, many=True).data
    return []


def _homestead_widget_content(key: str, user) -> list:
    """Assemble content for a Homestead hub widget (Node Spec 25), permission-filtered."""
    from apps.homestead import selectors as h
    from apps.homestead.serializers import (
        ApplianceSerializer,
        ImprovementSerializer,
        MaintenanceTaskSerializer,
    )

    if key == "homestead_maintenance":
        tasks = h.list_maintenance(user, due_only=True, limit=8)
        return MaintenanceTaskSerializer(tasks, many=True).data

    if key == "homestead_warranties":
        appliances = h.list_appliances(user, expiring_only=True, limit=8)
        return ApplianceSerializer(appliances, many=True).data

    if key == "homestead_improvements":
        improvements = h.list_improvements(user, open_only=True, limit=8)
        return ImprovementSerializer(improvements, many=True).data

    return []


def _solace_widget_content(key: str, user) -> list:
    """Assemble content for Solace finance widgets.

    Callers must pass this only after password re-auth. This function still checks the
    central resolver so finance widgets never appear for unauthorised roles.
    """
    from apps.permissions.resolver import resolve_permission
    from apps.solace import selectors as s
    from apps.solace.serializers import (
        BillSerializer,
        PlannedPurchaseSerializer,
    )

    if not resolve_permission(user, "view", "solace"):
        return []

    if key == "solace_bills_due":
        from datetime import timedelta

        from django.utils import timezone

        from apps.solace.bill_schedule import ensure_bill_occurrences
        from apps.solace.models import BillOccurrence

        bills = s.list_bills(user, upcoming_only=True, unpaid_only=True, active_only=True)
        today = timezone.localdate()
        for bill in bills:
            ensure_bill_occurrences(bill, today - timedelta(days=30), today + timedelta(days=90))
            bill._solace_next_occurrence = bill.occurrences.filter(
                status=BillOccurrence.Status.UPCOMING,
            ).order_by("due_at").first()
        bills.sort(
            key=lambda bill: (
                getattr(bill, "_solace_next_occurrence", None).due_at
                if getattr(bill, "_solace_next_occurrence", None)
                else None
                or bill.due_at
                or timezone.now() + timedelta(days=3650)
            )
        )
        return BillSerializer(bills[:8], many=True).data

    if key == "solace_subscriptions":
        subscriptions = [
            bill
            for bill in s.list_bills(user, active_only=True)
            if (bill.category or "").strip().casefold() in {"subscription", "subscriptions"}
        ]
        return BillSerializer(subscriptions[:8], many=True).data

    if key == "solace_planned_purchases":
        return PlannedPurchaseSerializer(
            s.list_purchases(user, open_only=True, limit=8), many=True
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


def set_household_widget(user, key: str, *, is_enabled=None, display_order=None, size=None, settings=None):
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
    if settings is not None:
        if key != "countdown":
            raise HubError("Settings are not supported for this widget.")
        config.settings_json = dict(settings)
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


def set_user_widget_order(user, keys: list[str]) -> None:
    """Persist the caller's complete enabled-widget order in one API round trip."""
    from apps.hub.models import HubWidget, UserHubWidget
    from apps.hub.selectors import list_widget_config

    config = [row for row in list_widget_config(user) if row["household_enabled"]]
    allowed = {row["key"] for row in config}
    if not set(keys).issubset(allowed) or not keys:
        raise HubError("Only enabled widgets can be reordered.")
    # The live Hub omits personally hidden widgets. Append any omitted rows in their current
    # effective order so dragging visible cards still leaves a complete, collision-free order.
    requested = set(keys)
    keys = [*keys, *(row["key"] for row in config if row["key"] not in requested)]

    widgets = {
        widget.key: widget for widget in HubWidget.objects.filter(key__in=keys)
    }
    existing = {
        row.widget_id: row
        for row in UserHubWidget.objects.filter(
            user=user, widget__in=widgets.values()
        )
    }
    to_create = []
    to_update = []
    for position, key in enumerate(keys):
        widget = widgets[key]
        row = existing.get(widget.id)
        if row is None:
            to_create.append(UserHubWidget(
                user=user, widget=widget, display_order=position
            ))
        elif row.display_order != position:
            row.display_order = position
            to_update.append(row)
    with transaction.atomic():
        if to_create:
            UserHubWidget.objects.bulk_create(to_create)
        if to_update:
            UserHubWidget.objects.bulk_update(to_update, ["display_order"])
