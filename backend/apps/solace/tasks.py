"""Cron-driven Solace reminders.

Reminder text deliberately contains no bill names or amounts because HomeStack's notification
drawer is available after PIN login while Solace details require password re-authentication.
"""
from __future__ import annotations

from datetime import date, timedelta

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.notifications.models import Notification
from apps.notifications.services import create_notification
from apps.permissions.resolver import resolve_permission
from apps.solace import selectors
from apps.solace.bill_schedule import ensure_bill_occurrences, household_timezone
from apps.solace.models import BillOccurrence


def send_due_reminders(*, on: date | None = None) -> int:
    from django.utils import timezone

    tz = household_timezone(get_active_household())
    on = on or timezone.localdate(timezone=tz)
    settings_obj = selectors.get_settings()
    if settings_obj is None or not settings_obj.dashboard_reminders:
        return 0
    window_end = on + timedelta(days=settings_obj.due_soon_days)
    for bill in selectors.list_bills(active_only=True):
        ensure_bill_occurrences(bill, on - timedelta(days=365), window_end)
    bill_attention = BillOccurrence.objects.filter(
        bill__deleted_at__isnull=True,
        bill__is_active=True,
        status=BillOccurrence.Status.UPCOMING,
        due_at__date__gte=on - timedelta(days=365),
        due_at__date__lte=window_end,
    ).exists()
    from apps.solace.budget_engine import payday_occurrences

    payday_attention = any(
        payday_occurrences(payday, on, window_end)
        for payday in selectors.list_paydays(active_only=True)
    )
    purchase_attention = any(
        row.target_date
        and on - timedelta(days=365) <= timezone.localdate(row.target_date, tz) <= window_end
        for row in selectors.list_purchases(open_only=True)
    )
    needs_attention = (
        bill_attention
        or payday_attention
        or purchase_attention
    )
    if not needs_attention:
        return 0

    action_url = f"/solace?tab=schedule&reminder={on.isoformat()}"
    created = 0
    for user in User.objects.filter(is_active=True):
        if not resolve_permission(user, "view", "solace"):
            continue
        if Notification.objects.filter(
            recipient_user=user,
            source_node="solace",
            action_url=action_url,
        ).exists():
            continue
        create_notification(
            user,
            title="Solace needs attention",
            message="Open Solace to review upcoming finance reminders.",
            level=Notification.Level.WARNING,
            source_node="solace",
            action_url=action_url,
        )
        created += 1
    return created
