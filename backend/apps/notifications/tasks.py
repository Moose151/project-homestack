"""Scheduled reminders + countdown digest — docs/32_Core_Notifications_and_Push.md §8/§9.

An hourly cron entry point (matching apps.solace/apps.link_imports' `*_run_scheduled`
pattern). Everything here is idempotent via NotificationReminderLog, so a missed run, a
re-run, or an overlapping run never double-sends.

Scope is deliberately narrow, matching docs/32 §8's "not the fully generic configurable lead
times" framing: only standalone Calendar entries and Atlas-sourced ones are swept. Other
synced nodes (Solace, Meridian, Homestead, Pets, Travel, Education) either already run their
own reminder job (Solace) or are simply out of scope for this feature — sweeping them in would
risk duplicate/unrequested notifications for something the owner didn't ask this command to
cover.
"""
from __future__ import annotations

from datetime import date, datetime
from datetime import time as time_cls
from datetime import timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.notifications.models import (
    NotificationCategory,
    NotificationPreference,
    NotificationReminderLog,
)
from apps.notifications import wording
from apps.notifications.services import create_notification, get_or_create_settings
from apps.permissions.visibility import apply_visibility


def _household_timezone(household) -> ZoneInfo:
    name = getattr(household, "timezone", "") or "UTC"
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _reminder_events():
    from apps.atlas.models import AtlasReminder
    from apps.scheduling.models import CalendarEvent

    disabled_reminder_ids = AtlasReminder.objects.filter(
        notifications_enabled=False,
    ).values_list("id", flat=True)
    return CalendarEvent.objects.filter(
        Q(source_node__isnull=True) | Q(source_node__key="atlas"),
        start_at__isnull=False,
    ).exclude(
        source_record_type="AtlasReminder", source_record_id__in=disabled_reminder_ids,
    )


def _category_and_source(event) -> tuple[str, str]:
    if event.source_node_id:
        return NotificationCategory.ASSIGNED_TASKS, "atlas"
    return NotificationCategory.APPOINTMENTS, "scheduling"


def _already_sent(*, source_node, record_type="CalendarEvent", record_id, lead_kind, recipient_user=None) -> bool:
    return NotificationReminderLog.objects.filter(
        source_node=source_node, record_type=record_type, record_id=record_id,
        lead_kind=lead_kind, recipient_user=recipient_user,
    ).exists()


def _log_sent(*, source_node, record_type="CalendarEvent", record_id, lead_kind, recipient_user=None) -> None:
    NotificationReminderLog.objects.create(
        household=get_active_household(), source_node=source_node, record_type=record_type,
        record_id=record_id, lead_kind=lead_kind, recipient_user=recipient_user,
    )


def _recipients_for(event, category: str) -> list[User]:
    """Household members who can see this event, filtered by their mine_only preference
    (docs/32 §3: mine_only=True means only notify for items assigned to them personally)."""
    assignee_ids = set(
        event.assigned_to_people.exclude(linked_user__isnull=True).values_list("linked_user_id", flat=True)
    )
    qs = type(event).objects.filter(pk=event.pk)
    recipients = []
    for user in User.objects.filter(is_active=True, household_id=event.household_id):
        if not apply_visibility(qs, user).exists():
            continue
        pref = NotificationPreference.objects.filter(user=user, category=category).first()
        mine_only = pref.mine_only if pref else False
        if event.source_record_type == "AtlasReminder" and assignee_ids and user.id not in assignee_ids:
            continue
        if mine_only and user.id not in assignee_ids:
            continue
        recipients.append(user)
    return recipients


def _action_url(event, tz) -> str:
    if event.source_record_type == "AtlasReminder" and event.source_record_id:
        return f"/atlas?tab=reminders&reminder={event.source_record_id}"
    return f"/calendar?date={event.start_at.astimezone(tz).date().isoformat()}"


def run_due_reminders(*, now=None) -> dict[str, int]:
    now = now or timezone.now()
    household = get_active_household()
    if household is None:
        return {"24h": 0, "morning_of": 0, "due_at": 0}
    tz = _household_timezone(household)
    local_now = now.astimezone(tz)
    sent_24h = sent_morning = sent_due = 0

    window_start = now + timedelta(hours=23)
    window_end = now + timedelta(hours=25)
    for event in _reminder_events().filter(start_at__gte=window_start, start_at__lte=window_end):
        category, source_node = _category_and_source(event)
        if _already_sent(source_node=source_node, record_id=event.id, lead_kind="24h"):
            continue
        for user in _recipients_for(event, category):
            create_notification(
                user, title=wording.tomorrow_title(event), message=event.title,
                source_node=source_node, category=category,
                action_url=_action_url(event, tz),
            )
        _log_sent(source_node=source_node, record_id=event.id, lead_kind="24h")
        sent_24h += 1

    # Reminders are the one entry kind the owner sets an exact time on expecting to hear about
    # it *then*, so they also fire at the scheduled moment itself. Scoped to Atlas reminders on
    # purpose: sweeping every appointment here would notify people at the instant a meeting
    # starts, which nobody asked for. All-day reminders have no meaningful time — the morning-of
    # lead already covers them. The window matches the hourly cron, so a reminder whose time has
    # already slipped past by more than one sweep is not resurrected.
    due_window_start = now - timedelta(hours=1)
    for event in _reminder_events().filter(
        source_record_type="AtlasReminder", is_all_day=False,
        start_at__gt=due_window_start, start_at__lte=now,
    ):
        category, source_node = _category_and_source(event)
        if _already_sent(source_node=source_node, record_id=event.id, lead_kind="due_at"):
            continue
        for user in _recipients_for(event, category):
            create_notification(
                user, title=wording.due_now_title(event), message=event.title,
                source_node=source_node, category=category,
                action_url=_action_url(event, tz),
            )
        _log_sent(source_node=source_node, record_id=event.id, lead_kind="due_at")
        sent_due += 1

    today = local_now.date()
    day_start = datetime.combine(today, time_cls.min, tzinfo=tz)
    day_end = day_start + timedelta(days=1)
    due_today = list(_reminder_events().filter(start_at__gte=day_start, start_at__lt=day_end))
    for event in due_today:
        category, source_node = _category_and_source(event)
        for user in _recipients_for(event, category):
            settings_obj = get_or_create_settings(user)
            if local_now.hour != settings_obj.morning_time.hour:
                continue
            if _already_sent(
                source_node=source_node, record_id=event.id, lead_kind="morning_of", recipient_user=user,
            ):
                continue
            create_notification(
                user, title=wording.today_title(event, tz), message=event.title,
                source_node=source_node, category=category,
                action_url=_action_url(event, tz),
            )
            _log_sent(
                source_node=source_node, record_id=event.id, lead_kind="morning_of", recipient_user=user,
            )
            sent_morning += 1

    return {"24h": sent_24h, "morning_of": sent_morning, "due_at": sent_due}


def _format_countdown(remaining: timedelta) -> str:
    total_seconds = max(0, int(remaining.total_seconds()))
    days = total_seconds // 86400
    if days >= 1:
        return f"{days} day{'s' if days != 1 else ''} to go"
    hours = max(1, total_seconds // 3600)
    return f"{hours} hour{'s' if hours != 1 else ''} to go"


def run_countdown_digest(*, now=None) -> dict[str, int]:
    now = now or timezone.now()
    household = get_active_household()
    if household is None:
        return {"sent": 0}
    tz = _household_timezone(household)
    local_now = now.astimezone(tz)

    from apps.hub.models import HouseholdHubWidget

    widget_row = HouseholdHubWidget.objects.filter(
        household=household, widget__key="countdown", is_enabled=True,
    ).first()
    if widget_row is None:
        return {"sent": 0}
    meta = widget_row.settings_json or {}
    target_date = meta.get("target_date")
    if not target_date:
        return {"sent": 0}
    try:
        target_at = datetime.combine(
            date.fromisoformat(target_date),
            time_cls.fromisoformat(meta.get("target_time") or "12:00"),
            tzinfo=tz,
        )
    except (TypeError, ValueError):
        return {"sent": 0}
    if target_at < now:
        return {"sent": 0}

    lead_kind = f"daily:{local_now.date().isoformat()}"
    sent = 0
    for user in User.objects.filter(is_active=True, household_id=household.id):
        settings_obj = get_or_create_settings(user)
        if local_now.hour != settings_obj.morning_time.hour:
            continue
        if _already_sent(
            source_node="hub", record_type="HouseholdHubWidget", record_id=widget_row.id,
            lead_kind=lead_kind, recipient_user=user,
        ):
            continue
        create_notification(
            user, title=meta.get("title") or "Countdown",
            message=_format_countdown(target_at - now),
            source_node="hub", category=NotificationCategory.COUNTDOWN, action_url="/hub",
        )
        _log_sent(
            source_node="hub", record_type="HouseholdHubWidget", record_id=widget_row.id,
            lead_kind=lead_kind, recipient_user=user,
        )
        sent += 1
    return {"sent": sent}
