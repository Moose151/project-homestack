"""homestead selectors — read-only queries (Coding Standards §6, D9)."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import connection
from django.db.models import Q
from django.utils import timezone

from apps.homestead import pool_care
from apps.homestead.models import (
    Appliance,
    HouseholdCost,
    Improvement,
    InsurancePolicy,
    MaintenanceTask,
    Pool,
    Property,
    RoomArea,
    RoomPlanItem,
    RoomPlanProduct,
    ServiceProvider,
    UtilityBill,
    WaterTest,
)
from apps.permissions.visibility import apply_visibility

_CLOSED_STATUSES = (Improvement.Status.DONE, Improvement.Status.CANCELLED)


def _search(qs, query: str, fields: list[str]):
    """Filter ``qs`` by ``query`` across ``fields`` (D9). Postgres FTS in prod, icontains on SQLite."""
    if connection.vendor == "postgresql":
        from django.contrib.postgres.search import SearchQuery, SearchVector
        return qs.annotate(_search=SearchVector(*fields)).filter(_search=SearchQuery(query))
    clause = Q()
    for field in fields:
        clause |= Q(**{f"{field}__icontains": query})
    return qs.filter(clause)


# ---------------------------------------------------------------------------
# Property
# ---------------------------------------------------------------------------

def list_properties(user=None):
    qs = Property.objects.order_by("-is_primary", "name")
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_property(pk: int, user=None) -> Property | None:
    qs = Property.objects.filter(pk=pk)
    if user is not None:
        qs = apply_visibility(qs, user)
    return qs.first()


# ---------------------------------------------------------------------------
# Service providers
# ---------------------------------------------------------------------------

def list_providers(user=None):
    qs = ServiceProvider.objects.order_by("name")
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_provider(pk: int, user=None) -> ServiceProvider | None:
    qs = ServiceProvider.objects.filter(pk=pk)
    if user is not None:
        qs = apply_visibility(qs, user)
    return qs.first()


# ---------------------------------------------------------------------------
# Appliances
# ---------------------------------------------------------------------------

def list_appliances(user=None, *, expiring_only: bool = False, within_days: int = 60,
                    limit: int | None = None):
    qs = Appliance.objects.order_by("name")
    if expiring_only:
        cutoff = timezone.now().date() + timedelta(days=within_days)
        qs = qs.filter(warranty_expires_at__isnull=False, warranty_expires_at__lte=cutoff)
        qs = qs.order_by("warranty_expires_at")
    if user is not None:
        qs = apply_visibility(qs, user)
    if limit is not None:
        qs = qs[:limit]
    return list(qs)


def get_appliance(pk: int, user=None) -> Appliance | None:
    qs = Appliance.objects.filter(pk=pk)
    if user is not None:
        qs = apply_visibility(qs, user)
    return qs.first()


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------

def list_maintenance(user=None, *, due_only: bool = False, limit: int | None = None):
    qs = MaintenanceTask.objects.select_related("appliance", "provider").order_by(
        "next_due_at", "-updated_at"
    )
    if due_only:
        qs = qs.filter(next_due_at__isnull=False)
    if user is not None:
        qs = apply_visibility(qs, user)
    if limit is not None:
        qs = qs[:limit]
    return list(qs)


def get_maintenance(pk: int, user=None) -> MaintenanceTask | None:
    qs = MaintenanceTask.objects.filter(pk=pk)
    if user is not None:
        qs = apply_visibility(qs, user)
    return qs.first()


# ---------------------------------------------------------------------------
# Improvements
# ---------------------------------------------------------------------------

def list_improvements(user=None, *, open_only: bool = False, limit: int | None = None):
    qs = Improvement.objects.order_by("-updated_at")
    if open_only:
        qs = qs.exclude(status__in=_CLOSED_STATUSES)
    if user is not None:
        qs = apply_visibility(qs, user)
    if limit is not None:
        qs = qs[:limit]
    return list(qs)


def get_improvement(pk: int, user=None) -> Improvement | None:
    qs = Improvement.objects.filter(pk=pk)
    if user is not None:
        qs = apply_visibility(qs, user)
    return qs.first()


# ---------------------------------------------------------------------------
# Rooms / areas and their unified plans
# ---------------------------------------------------------------------------

_EMPTY_ROOM_SUMMARY = {
    "active_count": 0,
    "completed_count": 0,
    "archived_count": 0,
    "remaining_estimated_cost": "0.00",
    "completed_cost": "0.00",
    "overall_cost": "0.00",
}


def empty_room_summary() -> dict:
    return dict(_EMPTY_ROOM_SUMMARY)


def list_rooms(user=None) -> list[RoomArea]:
    qs = RoomArea.objects.order_by("display_order", "name", "id")
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_room(pk: int, user=None) -> RoomArea | None:
    qs = RoomArea.objects.filter(pk=pk)
    if user is not None:
        qs = apply_visibility(qs, user)
    return qs.first()


def list_room_items(user, room: RoomArea) -> list[RoomPlanItem]:
    qs = RoomPlanItem.objects.filter(room=room).prefetch_related(
        "assigned_to_people", "products"
    )
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs.order_by("position", "-updated_at", "id"))


def get_room_item(pk: int, room: RoomArea, user=None) -> RoomPlanItem | None:
    qs = RoomPlanItem.objects.filter(pk=pk, room=room)
    if user is not None:
        qs = apply_visibility(qs, user)
    return qs.first()


def list_room_products(item: RoomPlanItem) -> list[RoomPlanProduct]:
    """Shopping-list options for one plan item.

    Visibility is carried by the parent plan item — the caller has already resolved that —
    so options are not filtered again here.
    """
    return list(RoomPlanProduct.objects.filter(plan_item=item).order_by("position", "id"))


def get_room_product(pk: int, item: RoomPlanItem) -> RoomPlanProduct | None:
    return RoomPlanProduct.objects.filter(pk=pk, plan_item=item).first()


def summarize_room_items(items: list[RoomPlanItem]) -> dict:
    remaining = Decimal("0.00")
    completed = Decimal("0.00")
    active_count = completed_count = archived_count = 0
    for item in items:
        if item.status in (RoomPlanItem.Status.PLANNED, RoomPlanItem.Status.IN_PROGRESS):
            active_count += 1
            remaining += item.estimated_total
        elif item.status == RoomPlanItem.Status.COMPLETED:
            completed_count += 1
            completed += item.effective_cost
        else:
            archived_count += 1
    return {
        "active_count": active_count,
        "completed_count": completed_count,
        "archived_count": archived_count,
        "remaining_estimated_cost": f"{remaining:.2f}",
        "completed_cost": f"{completed:.2f}",
        "overall_cost": f"{remaining + completed:.2f}",
    }


def room_summaries(user, rooms: list[RoomArea]) -> tuple[dict[int, dict], dict]:
    by_room = {room.id: [] for room in rooms}
    if rooms:
        qs = RoomPlanItem.objects.filter(room_id__in=by_room).prefetch_related("products")
        qs = apply_visibility(qs, user)
        for item in qs:
            by_room[item.room_id].append(item)
    summaries = {room_id: summarize_room_items(items) for room_id, items in by_room.items()}
    active_count = completed_count = archived_count = 0
    remaining = completed = overall = Decimal("0.00")
    for summary in summaries.values():
        active_count += summary["active_count"]
        completed_count += summary["completed_count"]
        archived_count += summary["archived_count"]
        remaining += Decimal(summary["remaining_estimated_cost"])
        completed += Decimal(summary["completed_cost"])
        overall += Decimal(summary["overall_cost"])
    household = {
        "active_count": active_count,
        "completed_count": completed_count,
        "archived_count": archived_count,
        "remaining_estimated_cost": f"{remaining:.2f}",
        "completed_cost": f"{completed:.2f}",
        "overall_cost": f"{overall:.2f}",
    }
    return summaries, household


# ---------------------------------------------------------------------------
# Protected home finances
# ---------------------------------------------------------------------------

def list_insurance_policies(user=None, *, active_only: bool = False):
    qs = InsurancePolicy.objects.order_by("next_renewal_at", "name")
    if active_only:
        qs = qs.filter(is_active=True)
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_insurance_policy(pk: int, user=None) -> InsurancePolicy | None:
    qs = InsurancePolicy.objects.filter(pk=pk)
    if user is not None:
        qs = apply_visibility(qs, user)
    return qs.first()


def list_household_costs(user=None, *, active_only: bool = False):
    qs = HouseholdCost.objects.order_by("next_due_at", "name")
    if active_only:
        qs = qs.filter(is_active=True)
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_household_cost(pk: int, user=None) -> HouseholdCost | None:
    qs = HouseholdCost.objects.filter(pk=pk)
    if user is not None:
        qs = apply_visibility(qs, user)
    return qs.first()


# ---------------------------------------------------------------------------
# Utility usage
# ---------------------------------------------------------------------------

def list_utility_bills(user=None, *, utility_type: str | None = None,
                       limit: int | None = None):
    qs = UtilityBill.objects.order_by("-period_end", "-id")
    if utility_type:
        qs = qs.filter(utility_type=utility_type)
    if user is not None:
        qs = apply_visibility(qs, user)
    if limit is not None:
        qs = qs[:limit]
    return list(qs)


def get_utility_bill(pk: int, user=None) -> UtilityBill | None:
    qs = UtilityBill.objects.filter(pk=pk)
    if user is not None:
        qs = apply_visibility(qs, user)
    return qs.first()


def _period_point(bill: UtilityBill) -> dict:
    return {
        "id": bill.id,
        "label": _period_label(bill),
        "period_start": bill.period_start,
        "period_end": bill.period_end,
        "days": bill.days,
        "usage_amount": bill.usage_amount,
        "daily_usage": bill.daily_usage,
        "amount": bill.amount,
        "daily_cost": bill.daily_cost,
        "unit_cost": bill.unit_cost,
        "is_estimated": bill.is_estimated,
    }


def _period_label(bill: UtilityBill) -> str:
    """A short axis label. One month reads as "Jun 25"; a quarter as "Apr–Jun 25"."""
    end = bill.period_end.strftime("%b %y")
    if (bill.period_start.year, bill.period_start.month) == (
        bill.period_end.year, bill.period_end.month
    ):
        return end
    return f"{bill.period_start.strftime('%b')}–{end}"


def _percent_change(current, previous) -> Decimal | None:
    """Change from `previous` to `current`, or None when there is nothing to divide by."""
    if previous in (None, 0) or current is None:
        return None
    return (
        (Decimal(current) - Decimal(previous)) / Decimal(previous) * 100
    ).quantize(Decimal("0.1"))


def _change_row(label: str, latest: UtilityBill, other: UtilityBill | None) -> dict | None:
    """Compare two periods per day, because bills are not the same length.

    A 92-day summer quarter next to an 88-day autumn one would otherwise look 5% worse before
    anyone turned anything on.
    """
    if other is None:
        return None
    return {
        "label": label,
        "usage_percent": _percent_change(latest.daily_usage, other.daily_usage),
        "cost_percent": _percent_change(latest.daily_cost, other.daily_cost),
    }


def _year_ago_bill(latest: UtilityBill, bills: list[UtilityBill]) -> UtilityBill | None:
    """The bill covering roughly this time last year — the comparison that means something.

    Utilities are seasonal, so the previous period is the wrong yardstick on its own. Billing
    dates drift, so match the closest period start within six weeks of a year earlier rather
    than demanding an exact date.
    """
    target = latest.period_start - timedelta(days=365)
    candidates = [
        bill for bill in bills
        if bill.id != latest.id and abs((bill.period_start - target).days) <= 45
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda bill: abs((bill.period_start - target).days))


def utility_usage(user=None, *, utility_type: str | None = None) -> list[dict]:
    """One series per utility the household has bills for, oldest period first.

    The screen is a set of charts, so every number a chart needs is computed here — averages
    are per day for the same reason the comparisons are.
    """
    bills = list_utility_bills(user, utility_type=utility_type)
    by_type: dict[str, list[UtilityBill]] = {}
    for bill in bills:
        by_type.setdefault(bill.utility_type, []).append(bill)

    series = []
    for type_key, rows in by_type.items():
        rows = sorted(rows, key=lambda bill: (bill.period_end, bill.id))
        latest = rows[-1]
        total_usage = sum((bill.usage_amount for bill in rows), Decimal("0"))
        total_cost = sum((bill.amount for bill in rows), Decimal("0.00"))
        total_days = sum(bill.days for bill in rows)
        changes = [
            row for row in (
                _change_row("vs previous bill", latest, rows[-2] if len(rows) > 1 else None),
                _change_row("vs a year ago", latest, _year_ago_bill(latest, rows)),
            ) if row is not None
        ]
        series.append({
            "utility_type": type_key,
            "label": UtilityBill.UtilityType(type_key).label,
            # Mixed units in one series would silently add kL to litres, so the newest bill's
            # unit names the series and the chart stays one measure.
            "unit_label": latest.unit_label,
            "bill_count": len(rows),
            "total_usage": total_usage,
            "total_cost": total_cost,
            "average_daily_usage": (total_usage / total_days).quantize(Decimal("0.001")),
            "average_daily_cost": (total_cost / total_days).quantize(Decimal("0.01")),
            "average_unit_cost": (
                (total_cost / total_usage).quantize(Decimal("0.0001"))
                if total_usage else None
            ),
            "latest": _period_point(latest),
            "changes": changes,
            "periods": [_period_point(bill) for bill in rows],
        })
    series.sort(key=lambda row: row["label"])
    return series


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search_homestead(user, query: str) -> dict:
    """Permission-filtered FTS across the Homestead surfaces (D9, Node Spec 25)."""
    appliances_qs = _search(
        Appliance.objects.all(), query,
        ["name", "brand", "model_number", "serial_number", "room", "notes"],
    )
    tasks_qs = _search(MaintenanceTask.objects.all(), query, ["title", "notes"])
    providers_qs = _search(
        ServiceProvider.objects.all(), query, ["name", "company", "notes"]
    )
    improvements_qs = _search(
        Improvement.objects.all(), query, ["title", "description", "room", "notes"]
    )
    rooms_qs = _search(RoomArea.objects.all(), query, ["name", "description"])
    room_items_qs = _search(
        RoomPlanItem.objects.select_related("room"), query,
        ["title", "description", "notes"],
    )
    if user is not None:
        appliances_qs = apply_visibility(appliances_qs, user)
        tasks_qs = apply_visibility(tasks_qs, user)
        providers_qs = apply_visibility(providers_qs, user)
        improvements_qs = apply_visibility(improvements_qs, user)
        rooms_qs = apply_visibility(rooms_qs, user)
        room_items_qs = apply_visibility(room_items_qs, user).filter(
            room_id__in=apply_visibility(RoomArea.objects.all(), user).values("id")
        )
    return {
        "appliances": list(appliances_qs.order_by("name")),
        "maintenance": list(tasks_qs.order_by("next_due_at")),
        "providers": list(providers_qs.order_by("name")),
        "improvements": list(improvements_qs.order_by("-updated_at")),
        "rooms": list(rooms_qs.order_by("display_order", "name")),
        "room_items": list(room_items_qs.order_by("room__name", "position")),
    }


# ---------------------------------------------------------------------------
# Pools and water tests
# ---------------------------------------------------------------------------

def list_pools(user=None, *, active_only: bool = False):
    qs = Pool.objects.select_related("room").order_by("name", "id")
    if active_only:
        qs = qs.filter(is_active=True)
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_pool(pk: int, user=None) -> Pool | None:
    qs = Pool.objects.filter(pk=pk)
    if user is not None:
        qs = apply_visibility(qs, user)
    return qs.first()


def list_water_tests(pool: Pool, *, limit: int | None = 30):
    qs = WaterTest.objects.filter(pool=pool).order_by("-tested_at", "-id")
    return list(qs[:limit] if limit else qs)


def get_water_test(pk: int, pool: Pool) -> WaterTest | None:
    return WaterTest.objects.filter(pk=pk, pool=pool).first()


def list_pool_care(user, pool: Pool):
    """The pool's own maintenance jobs, soonest first."""
    qs = MaintenanceTask.objects.filter(pool=pool).select_related("provider").order_by(
        "next_due_at", "-updated_at"
    )
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def pool_status(user, pool: Pool) -> dict:
    """Everything the pool screen needs to answer "is the water OK and what is due?".

    The assessment is computed from the current targets rather than stored, so a reading taken
    months ago is still judged against the guidance shipping today.
    """
    latest = WaterTest.objects.filter(pool=pool).order_by("-tested_at", "-id").first()
    readings = (
        pool_care.assess(latest.reading_values(), pool.sanitiser, pool.surface) if latest else {}
    )
    out_of_range = [key for key, row in readings.items() if row["status"] in ("low", "high")]
    care = list_pool_care(user, pool)
    now = timezone.now()
    overdue = [task for task in care if task.next_due_at and task.next_due_at < now]
    return {
        "latest_test_id": latest.id if latest else None,
        "latest_tested_at": latest.tested_at if latest else None,
        "readings": readings,
        "out_of_range": out_of_range,
        "water_is_balanced": bool(latest) and not out_of_range,
        "care_task_count": len(care),
        "overdue_task_count": len(overdue),
        "next_due_at": next((task.next_due_at for task in care if task.next_due_at), None),
    }


def pool_targets(pool: Pool) -> dict:
    return pool_care.targets_for(pool.sanitiser, pool.surface)
