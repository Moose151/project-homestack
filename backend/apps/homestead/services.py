"""homestead services — write operations (Coding Standards §6).

Maintenance (next_due_at) and improvements (target_date) mirror to the shared calendar via the
scheduling helper only (D7) — never CalendarEvent.objects directly.
"""
from __future__ import annotations

from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.homestead import events
from apps.homestead.models import (
    Appliance,
    Improvement,
    MaintenanceTask,
    Property,
    ServiceProvider,
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
    "appliance_id", "provider_id", "assigned_to_person_id", "title", "category",
    "next_due_at", "is_all_day", "recurrence_rule", "last_done_at", "notes", "visibility",
}


def create_maintenance(acting_user: User, **data) -> MaintenanceTask:
    obj = MaintenanceTask(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    sync_event_for(obj)
    return obj


def update_maintenance(acting_user: User, obj: MaintenanceTask, **data) -> MaintenanceTask:
    for key, val in data.items():
        if key in _TASK_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    sync_event_for(obj)
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
    sync_event_for(obj)
    events.maintenance_completed(obj.id, obj.household_id)
    return obj


def delete_maintenance(acting_user: User, obj: MaintenanceTask) -> None:
    delete_event_for(obj)
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


# ---------------------------------------------------------------------------
# Improvements
# ---------------------------------------------------------------------------

_IMPROVEMENT_FIELDS = {
    "assigned_to_person_id", "title", "description", "status", "priority",
    "room", "target_date", "is_all_day", "project_ref", "notes", "visibility",
}


def create_improvement(acting_user: User, **data) -> Improvement:
    obj = Improvement(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    sync_event_for(obj)
    events.improvement_created(obj.id, obj.household_id)
    return obj


def update_improvement(acting_user: User, obj: Improvement, **data) -> Improvement:
    was_open = obj.is_open
    for key, val in data.items():
        if key in _IMPROVEMENT_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    sync_event_for(obj)
    if was_open and not obj.is_open:
        events.improvement_completed(obj.id, obj.household_id)
    return obj


def delete_improvement(acting_user: User, obj: Improvement) -> None:
    delete_event_for(obj)
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()
