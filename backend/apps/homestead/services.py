"""homestead services — write operations (Coding Standards §6).

Maintenance (next_due_at) and improvements (target_date) mirror to the shared calendar via the
scheduling helper only (D7) — never CalendarEvent.objects directly.
"""
from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import User
from apps.core.assignment import apply_assignees, pop_assignees
from apps.core.models import get_active_household
from apps.homestead import events
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
from apps.scheduling.helpers import delete_event_for, sync_event_for


# ---------------------------------------------------------------------------
# Property
# ---------------------------------------------------------------------------

_PROPERTY_FIELDS = {
    "name", "address", "property_type", "tenure", "purchase_date", "move_in_date",
    "year_built", "is_primary", "notes", "water_shutoff", "gas_shutoff",
    "electricity_consumer_unit", "boiler_location", "visibility",
}


def create_property(acting_user: User, **data) -> Property:
    obj = Property(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    events.property_created(obj.id, obj.household_id)
    return obj


def update_property(acting_user: User, obj: Property, **data) -> Property:
    for key, val in data.items():
        if key in _PROPERTY_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    return obj


def delete_property(acting_user: User, obj: Property) -> None:
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


# ---------------------------------------------------------------------------
# Service providers
# ---------------------------------------------------------------------------

_PROVIDER_FIELDS = {
    "name", "trade", "company", "phone", "email", "website", "last_used_at", "notes",
    "visibility",
}


def create_provider(acting_user: User, **data) -> ServiceProvider:
    obj = ServiceProvider(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    return obj


def update_provider(acting_user: User, obj: ServiceProvider, **data) -> ServiceProvider:
    for key, val in data.items():
        if key in _PROVIDER_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    return obj


def delete_provider(acting_user: User, obj: ServiceProvider) -> None:
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


# ---------------------------------------------------------------------------
# Appliances
# ---------------------------------------------------------------------------

_APPLIANCE_FIELDS = {
    "name", "category", "brand", "model_number", "serial_number", "room",
    "purchase_date", "warranty_expires_at", "warranty_provider", "manual_url", "notes",
    "visibility",
}


def create_appliance(acting_user: User, **data) -> Appliance:
    obj = Appliance(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    events.appliance_added(obj.id, obj.household_id)
    return obj


def update_appliance(acting_user: User, obj: Appliance, **data) -> Appliance:
    for key, val in data.items():
        if key in _APPLIANCE_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    return obj


def delete_appliance(acting_user: User, obj: Appliance) -> None:
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


# ---------------------------------------------------------------------------
# Maintenance tasks
# ---------------------------------------------------------------------------

_TASK_FIELDS = {
    "appliance_id", "provider_id", "pool_id", "title", "category",
    "next_due_at", "is_all_day", "recurrence_rule", "last_done_at", "notes", "visibility",
    "solace_bill_ref",
}


def _sync_maintenance_calendar(obj: MaintenanceTask) -> None:
    # A Solace-funded task already has one financial Calendar row. Keep Homestead as the
    # practical workspace without creating a second event for the same due date.
    if obj.solace_bill_ref:
        delete_event_for(obj)
    else:
        sync_event_for(obj)


def create_maintenance(acting_user: User, **data) -> MaintenanceTask:
    people = pop_assignees(data)
    obj = MaintenanceTask(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    apply_assignees(obj, people)
    _sync_maintenance_calendar(obj)
    events.maintenance_saved(obj, acting_user.id)
    return obj


def update_maintenance(acting_user: User, obj: MaintenanceTask, **data) -> MaintenanceTask:
    people = pop_assignees(data)
    for key, val in data.items():
        if key in _TASK_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    apply_assignees(obj, people)
    _sync_maintenance_calendar(obj)
    events.maintenance_saved(obj, acting_user.id)
    return obj


def _next_occurrence(recurrence_rule: str, after):
    """Next datetime from an RRULE strictly after ``after``, or None (D8, dateutil)."""
    if not recurrence_rule:
        return None
    try:
        from dateutil.rrule import rrulestr
        rule = rrulestr(recurrence_rule, dtstart=after)
        return rule.after(after, inc=False)
    except (ValueError, TypeError):
        return None


def complete_maintenance(acting_user: User, obj: MaintenanceTask) -> MaintenanceTask:
    """Mark a task done: stamp last_done_at and advance next_due_at by its RRULE.

    Non-recurring tasks have their reminder cleared (next_due_at -> None) so they leave the "due"
    lists; the completion still stamps last_done_at for history. Re-syncs the calendar.
    """
    now = timezone.now()
    obj.last_done_at = now
    obj.next_due_at = _next_occurrence(obj.recurrence_rule, now)
    obj.updated_by = acting_user
    obj.save()
    _sync_maintenance_calendar(obj)
    events.maintenance_saved(obj, acting_user.id)
    events.maintenance_completed(obj.id, obj.household_id)
    return obj


def delete_maintenance(acting_user: User, obj: MaintenanceTask) -> None:
    delete_event_for(obj)
    events.maintenance_deleted(obj, acting_user.id)
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


def request_maintenance_cost(
    acting_user: User, obj: MaintenanceTask, *, amount, category: str = "other"
) -> MaintenanceTask:
    """Create/update the task's single Solace bill without importing Solace models."""
    events.maintenance_cost_requested(
        obj,
        acting_user.id,
        amount=amount,
        category=category,
    )
    obj.refresh_from_db()
    if not obj.solace_bill_ref:
        raise RuntimeError("Solace did not return a linked bill.")
    _sync_maintenance_calendar(obj)
    return obj


_RRULE_CYCLES = (
    ("FREQ=WEEKLY;INTERVAL=2", "fortnightly"),
    ("FREQ=WEEKLY", "weekly"),
    ("FREQ=MONTHLY;INTERVAL=6", "half_yearly"),
    ("FREQ=MONTHLY;INTERVAL=3", "quarterly"),
    ("FREQ=MONTHLY", "monthly"),
    ("FREQ=YEARLY", "yearly"),
)


def _billing_cycle(recurrence_rule: str) -> str:
    normalised = recurrence_rule.upper()
    for prefix, cycle in _RRULE_CYCLES:
        if normalised.startswith(prefix):
            return cycle
    return "other"


def _cost_type(category: str, name: str) -> str:
    category = category.lower()
    if category == "mortgage":
        return HouseholdCost.CostType.MORTGAGE
    if category == "council":
        return HouseholdCost.CostType.RATES
    lowered = name.lower()
    for keyword, cost_type in (
        ("mortgage", HouseholdCost.CostType.MORTGAGE),
        ("rent", HouseholdCost.CostType.MORTGAGE),
        ("council", HouseholdCost.CostType.RATES),
        ("rates", HouseholdCost.CostType.RATES),
        ("electric", HouseholdCost.CostType.ELECTRICITY),
        ("water", HouseholdCost.CostType.WATER),
        ("gas", HouseholdCost.CostType.GAS),
        ("internet", HouseholdCost.CostType.INTERNET),
        ("waste", HouseholdCost.CostType.WASTE),
        ("strata", HouseholdCost.CostType.BODY_CORPORATE),
        ("body corporate", HouseholdCost.CostType.BODY_CORPORATE),
    ):
        if keyword in lowered:
            return cost_type
    return HouseholdCost.CostType.OTHER


def organise_solace_bill(acting_user: User, *, destination: str, bill: dict):
    """Idempotently create or refresh Homestead's display/details record for a Solace bill."""
    bill_id = bill["bill_id"]
    household = get_active_household()
    shared = {
        "household": household,
        "created_by": acting_user,
        "updated_by": acting_user,
    }
    if destination == "insurance_policy":
        obj = InsurancePolicy.all_objects.filter(solace_bill_ref=bill_id).first()
        if obj is None:
            obj = InsurancePolicy(solace_bill_ref=bill_id, **shared)
        obj.deleted_at = None
        obj.name = bill["name"]
        obj.provider = bill.get("provider", "")
        obj.premium_amount = bill["amount"]
        obj.billing_cycle = _billing_cycle(bill.get("recurrence_rule", ""))
        obj.next_renewal_at = bill.get("due_at")
        obj.recurrence_rule = bill.get("recurrence_rule", "")
        obj.is_active = bill.get("is_active", True)
        obj.notes = bill.get("notes", "")
        obj.visibility = "sensitive"
        obj.updated_by = acting_user
        obj.save()
        record_type = "insurance_policy"
    elif destination == "household_cost":
        obj = HouseholdCost.all_objects.filter(solace_bill_ref=bill_id).first()
        if obj is None:
            obj = HouseholdCost(solace_bill_ref=bill_id, **shared)
        obj.deleted_at = None
        obj.name = bill["name"]
        obj.cost_type = _cost_type(bill.get("category", ""), bill["name"])
        obj.provider = bill.get("provider", "")
        obj.amount = bill["amount"]
        obj.billing_cycle = _billing_cycle(bill.get("recurrence_rule", ""))
        obj.next_due_at = bill.get("due_at")
        obj.recurrence_rule = bill.get("recurrence_rule", "")
        obj.is_active = bill.get("is_active", True)
        obj.notes = bill.get("notes", "")
        obj.visibility = "sensitive"
        obj.updated_by = acting_user
        obj.save()
        record_type = "household_cost"
    elif destination == "maintenance":
        provider = None
        if bill.get("provider"):
            provider = ServiceProvider.all_objects.filter(
                household=household, name__iexact=bill["provider"]
            ).first()
            if provider is None:
                provider = ServiceProvider(
                    name=bill["provider"], trade=ServiceProvider.Trade.OTHER,
                    visibility="sensitive", **shared,
                )
            provider.deleted_at = None
            provider.updated_by = acting_user
            provider.save()
        obj = MaintenanceTask.all_objects.filter(solace_bill_ref=bill_id).first()
        if obj is None:
            obj = MaintenanceTask(solace_bill_ref=bill_id, **shared)
        obj.deleted_at = None
        obj.title = bill["name"]
        obj.provider = provider
        obj.next_due_at = bill.get("due_at")
        obj.recurrence_rule = bill.get("recurrence_rule", "")
        obj.notes = bill.get("notes", "")
        obj.visibility = "sensitive"
        obj.updated_by = acting_user
        obj.save()
        _sync_maintenance_calendar(obj)
        record_type = "maintenance"
    else:
        raise ValueError("Unsupported Homestead destination.")

    events.solace_bill_linked(
        bill_id=bill_id,
        record_type=record_type,
        record_id=obj.id,
        household_id=obj.household_id,
        acting_user_id=acting_user.id,
    )
    return obj


def refresh_solace_bill_projection(acting_user: User, *, bill: dict) -> None:
    """Copy Solace-owned display values onto an existing Homestead details record."""
    bill_id = bill["bill_id"]
    if InsurancePolicy.all_objects.filter(solace_bill_ref=bill_id).exists():
        organise_solace_bill(acting_user, destination="insurance_policy", bill=bill)
    if HouseholdCost.all_objects.filter(solace_bill_ref=bill_id).exists():
        organise_solace_bill(acting_user, destination="household_cost", bill=bill)


def remove_solace_bill_projection(*, bill_id: int, household_id: int) -> None:
    """Hide Homestead details when their owning Solace bill is deleted."""
    deleted_at = timezone.now()
    InsurancePolicy.all_objects.filter(
        solace_bill_ref=bill_id, household_id=household_id, deleted_at__isnull=True
    ).update(deleted_at=deleted_at)
    HouseholdCost.all_objects.filter(
        solace_bill_ref=bill_id, household_id=household_id, deleted_at__isnull=True
    ).update(deleted_at=deleted_at)


# ---------------------------------------------------------------------------
# Improvements
# ---------------------------------------------------------------------------

_IMPROVEMENT_FIELDS = {
    "title", "description", "status", "priority",
    "room", "target_date", "is_all_day", "project_ref", "notes", "visibility",
}


def create_improvement(acting_user: User, **data) -> Improvement:
    people = pop_assignees(data)
    obj = Improvement(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    apply_assignees(obj, people)
    sync_event_for(obj)
    events.improvement_created(obj.id, obj.household_id)
    return obj


def update_improvement(acting_user: User, obj: Improvement, **data) -> Improvement:
    people = pop_assignees(data)
    was_open = obj.is_open
    for key, val in data.items():
        if key in _IMPROVEMENT_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    apply_assignees(obj, people)
    sync_event_for(obj)
    if was_open and not obj.is_open:
        events.improvement_completed(obj.id, obj.household_id)
    return obj


def delete_improvement(acting_user: User, obj: Improvement) -> None:
    delete_event_for(obj)
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


# ---------------------------------------------------------------------------
# Rooms / areas and their unified plans
# ---------------------------------------------------------------------------

_ROOM_FIELDS = {
    "name", "area_type", "description", "icon", "colour", "display_order",
    "floorplan_data", "visibility",
}
_ROOM_ITEM_FIELDS = {
    "title", "item_type", "status", "priority", "description",
    "plan_mode", "quantity", "estimated_unit_cost", "actual_cost", "notes", "position",
    "visibility",
}


def create_room(acting_user: User, **data) -> RoomArea:
    obj = RoomArea(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    events.room_created(obj.id, obj.household_id)
    return obj


def update_room(acting_user: User, obj: RoomArea, **data) -> RoomArea:
    for key, value in data.items():
        if key in _ROOM_FIELDS:
            setattr(obj, key, value)
    obj.updated_by = acting_user
    obj.save()
    return obj


def delete_room(acting_user: User, obj: RoomArea) -> None:
    for item in obj.plan_items.all():
        item.updated_by = acting_user
        item.save(update_fields=["updated_by", "updated_at"])
        item.soft_delete()
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


def create_room_item(
    acting_user: User, room: RoomArea, **data
) -> RoomPlanItem:
    people = pop_assignees(data)
    obj = RoomPlanItem(
        household=get_active_household(),
        room=room,
        created_by=acting_user,
        updated_by=acting_user,
        **data,
    )
    if obj.status == RoomPlanItem.Status.COMPLETED:
        obj.completed_at = timezone.now()
    obj.save()
    apply_assignees(obj, people)
    events.room_item_created(obj.id, room.id, obj.household_id)
    return obj


def update_room_item(
    acting_user: User, obj: RoomPlanItem, **data
) -> RoomPlanItem:
    people = pop_assignees(data)
    previous_status = obj.status
    for key, value in data.items():
        if key in _ROOM_ITEM_FIELDS:
            setattr(obj, key, value)
    if obj.status == RoomPlanItem.Status.COMPLETED and previous_status != obj.status:
        obj.completed_at = timezone.now()
    elif obj.status != RoomPlanItem.Status.COMPLETED:
        obj.completed_at = None
    obj.updated_by = acting_user
    obj.save()
    apply_assignees(obj, people)
    if previous_status != RoomPlanItem.Status.COMPLETED and obj.status == RoomPlanItem.Status.COMPLETED:
        events.room_item_completed(obj.id, obj.room_id, obj.household_id)
    return obj


def delete_room_item(acting_user: User, obj: RoomPlanItem) -> None:
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


# ---------------------------------------------------------------------------
# Room plan products — the shopping list behind one plan item
# ---------------------------------------------------------------------------

_ROOM_PRODUCT_FIELDS = {
    "title", "url", "image_url", "retailer", "quantity", "unit_cost",
    "is_chosen", "is_purchased", "actual_cost", "notes", "position",
}


def _apply_chosen_product(acting_user: User, product: RoomPlanProduct) -> None:
    """Make `product` the only chosen option and copy its price onto the plan item.

    Choosing an option is how a household says "this is the one" — so the room and
    whole-house estimates should follow it rather than keeping a stale number typed in
    before the options were compared.

    Projects have no chosen option: their parts are all required and their estimate is the
    sum of them, so copying one part's price onto the job would understate it.
    """
    item = product.plan_item
    if item.is_project:
        return
    RoomPlanProduct.objects.filter(plan_item=item).exclude(pk=product.pk).filter(
        is_chosen=True
    ).update(is_chosen=False)
    item.quantity = product.quantity
    item.estimated_unit_cost = product.unit_cost
    item.updated_by = acting_user
    item.save(update_fields=["quantity", "estimated_unit_cost", "updated_by", "updated_at"])


def create_room_product(
    acting_user: User, item: RoomPlanItem, **data
) -> RoomPlanProduct:
    obj = RoomPlanProduct(
        household=get_active_household(),
        plan_item=item,
        created_by=acting_user,
        updated_by=acting_user,
        **data,
    )
    obj.save()
    if obj.is_chosen:
        _apply_chosen_product(acting_user, obj)
    return obj


def update_room_product(
    acting_user: User, obj: RoomPlanProduct, **data
) -> RoomPlanProduct:
    became_chosen = data.get("is_chosen") and not obj.is_chosen
    for key, value in data.items():
        if key in _ROOM_PRODUCT_FIELDS:
            setattr(obj, key, value)
    obj.updated_by = acting_user
    obj.save()
    # Also re-apply when the chosen option's own price changes, so the estimate stays true.
    if obj.is_chosen and (became_chosen or "unit_cost" in data or "quantity" in data):
        _apply_chosen_product(acting_user, obj)
    return obj


def delete_room_product(acting_user: User, obj: RoomPlanProduct) -> None:
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


# ---------------------------------------------------------------------------
# Insurance policies
# ---------------------------------------------------------------------------

_POLICY_FIELDS = {
    "policy_type", "policy_number", "standard_excess", "additional_excesses",
    "coverage_summary", "contact_phone", "portal_url",
}


def create_insurance_policy(acting_user: User, **data) -> InsurancePolicy:
    obj = InsurancePolicy(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    obj.refresh_from_db()
    return obj


def update_insurance_policy(
    acting_user: User, obj: InsurancePolicy, **data
) -> InsurancePolicy:
    for key, val in data.items():
        if key in _POLICY_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    obj.refresh_from_db()
    return obj


def delete_insurance_policy(acting_user: User, obj: InsurancePolicy) -> None:
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


# ---------------------------------------------------------------------------
# Household costs
# ---------------------------------------------------------------------------

_COST_FIELDS = {
    "cost_type", "account_number",
}


def create_household_cost(acting_user: User, **data) -> HouseholdCost:
    obj = HouseholdCost(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    obj.refresh_from_db()
    return obj


def update_household_cost(
    acting_user: User, obj: HouseholdCost, **data
) -> HouseholdCost:
    for key, val in data.items():
        if key in _COST_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    obj.refresh_from_db()
    return obj


def delete_household_cost(acting_user: User, obj: HouseholdCost) -> None:
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


# ---------------------------------------------------------------------------
# Utility bills (metered usage)
# ---------------------------------------------------------------------------

_UTILITY_BILL_FIELDS = {
    "utility_type", "provider", "period_start", "period_end", "usage_amount",
    "usage_unit", "amount", "is_estimated", "notes", "visibility",
}


def log_utility_bill(acting_user: User, **data) -> UtilityBill:
    """Record a bill that has arrived. No calendar event: this is what already happened,
    while the recurring `HouseholdCost` owns when the next one is due (D7)."""
    if not data.get("usage_unit"):
        data["usage_unit"] = UtilityBill.DEFAULT_UNITS[
            data.get("utility_type", UtilityBill.UtilityType.ELECTRICITY)
        ]
    obj = UtilityBill(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    events.utility_bill_logged(obj, acting_user.id)
    return obj


def update_utility_bill(acting_user: User, obj: UtilityBill, **data) -> UtilityBill:
    for key, val in data.items():
        if key in _UTILITY_BILL_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    return obj


def delete_utility_bill(acting_user: User, obj: UtilityBill) -> None:
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


# ---------------------------------------------------------------------------
# Pools and water tests
# ---------------------------------------------------------------------------

_POOL_FIELDS = {
    "room_id", "name", "kind", "sanitiser", "surface", "filter_type", "volume_litres",
    "is_indoor", "equipment_notes", "notes", "is_active", "visibility",
}
_WATER_TEST_FIELDS = {
    "tested_at", "free_chlorine", "ph", "total_alkalinity", "calcium_hardness",
    "cyanuric_acid", "salt", "water_temp_c", "notes",
}


def create_pool(acting_user: User, *, with_care_schedule: bool = True, **data) -> Pool:
    """Add a pool. Unless told otherwise it arrives with its starter care schedule already set
    up, because a household that has never run a pool does not know what the jobs are."""
    obj = Pool(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    if with_care_schedule:
        apply_care_schedule(acting_user, obj)
    events.pool_saved(obj, acting_user.id)
    return obj


def update_pool(acting_user: User, obj: Pool, **data) -> Pool:
    for key, val in data.items():
        if key in _POOL_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    events.pool_saved(obj, acting_user.id)
    return obj


def delete_pool(acting_user: User, obj: Pool) -> None:
    # Its care jobs are real Calendar-synced maintenance, so release those events first.
    for task in obj.care_tasks.all():
        delete_maintenance(acting_user, task)
    events.pool_deleted(obj, acting_user.id)
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


def apply_care_schedule(acting_user: User, pool: Pool) -> list[MaintenanceTask]:
    """Create the starter care jobs this pool does not already have.

    Idempotent by title, so calling it again after switching to a salt cell adds only the jobs
    that switch introduced, and never duplicates or overwrites a job the household has edited.
    """
    existing = set(pool.care_tasks.values_list("title", flat=True))
    now = timezone.now()
    created = []
    for index, job in enumerate(pool_care.schedule_for(pool.sanitiser)):
        if job["title"] in existing:
            continue
        created.append(create_maintenance(
            acting_user,
            pool_id=pool.id,
            title=job["title"],
            category=MaintenanceTask.Category.POOL,
            # Stagger the first due dates so ten jobs do not all land on day one.
            next_due_at=now + timedelta(days=index),
            is_all_day=True,
            recurrence_rule=job["recurrence_rule"],
            notes=job["notes"],
            visibility=pool.visibility,
        ))
    return created


def log_water_test(acting_user: User, pool: Pool, **data) -> WaterTest:
    data.setdefault("tested_at", timezone.now())
    obj = WaterTest(
        pool=pool, household=get_active_household(),
        created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    events.water_test_logged(obj, acting_user.id)
    return obj


def update_water_test(acting_user: User, obj: WaterTest, **data) -> WaterTest:
    for key, val in data.items():
        if key in _WATER_TEST_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    return obj


def delete_water_test(acting_user: User, obj: WaterTest) -> None:
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()
