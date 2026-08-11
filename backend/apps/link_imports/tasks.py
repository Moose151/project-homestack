from __future__ import annotations

from datetime import time
from zoneinfo import ZoneInfo

from django.utils import timezone
from django.db import transaction

from apps.core.models import get_active_household
from apps.link_imports.models import LinkWatch
from apps.link_imports.services import check_watch


@transaction.atomic
def _claim_watch(watch_id: int, *, now, zone: ZoneInfo):
    watch = LinkWatch.objects.select_for_update().select_related("owner_person").filter(
        pk=watch_id, is_active=True,
    ).first()
    if watch is None:
        return None
    if watch.last_checked_at and watch.last_checked_at.astimezone(zone).date() == now.astimezone(zone).date():
        return None
    # Commit the claim before network I/O. Another hourly/overlapping command then skips it.
    watch.last_checked_at = now
    watch.save(update_fields=["last_checked_at", "updated_at"])
    return watch


def run_daily_price_watches(*, now=None) -> dict[str, int]:
    now = now or timezone.now()
    household = get_active_household()
    if household is None:
        return {"checked": 0, "alerts": 0}
    zone = ZoneInfo(household.timezone)
    local_now = now.astimezone(zone)
    if local_now.time() < time(9, 0):
        return {"checked": 0, "alerts": 0}
    due = LinkWatch.objects.filter(is_active=True)
    checked = alerts = 0
    for candidate in due.only("id"):
        watch = _claim_watch(candidate.id, now=now, zone=zone)
        if watch is None:
            continue
        checked += 1
        alerts += int(check_watch(watch, now=now))
    return {"checked": checked, "alerts": alerts}
