"""pets services — write operations (Coding Standards §6).

Treatments (next_due_at) and appointments (start_at) mirror to the shared calendar via the
scheduling helper only (D7) — never CalendarEvent.objects directly.
"""
from __future__ import annotations

from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.pets import events
from apps.pets.models import Pet, PetAppointment, PetTreatment
from apps.scheduling.helpers import delete_event_for, sync_event_for

# ---------------------------------------------------------------------------
# Pets
# ---------------------------------------------------------------------------

_PET_FIELDS = {
    "name", "species", "breed", "avatar", "colour", "date_of_birth", "adoption_date",
    "notes", "vet_name", "vet_phone", "microchip_number", "insurance_provider",
    "insurance_policy_number", "food_notes", "is_archived", "visibility",
}


def create_pet(acting_user: User, **data) -> Pet:
    obj = Pet(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    events.pet_created(obj.id, obj.household_id)
    return obj


def update_pet(acting_user: User, obj: Pet, **data) -> Pet:
    for key, val in data.items():
        if key in _PET_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    return obj


def delete_pet(acting_user: User, obj: Pet) -> None:
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


# ---------------------------------------------------------------------------
# Treatments
# ---------------------------------------------------------------------------

_TREATMENT_FIELDS = {
    "pet_id", "treatment_type", "name", "last_done_at", "next_due_at",
    "recurrence_rule", "notes", "visibility",
}


def create_treatment(acting_user: User, **data) -> PetTreatment:
    obj = PetTreatment(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    sync_event_for(obj)
    return obj


def update_treatment(acting_user: User, obj: PetTreatment, **data) -> PetTreatment:
    for key, val in data.items():
        if key in _TREATMENT_FIELDS:
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


def complete_treatment(acting_user: User, obj: PetTreatment) -> PetTreatment:
    """Mark a treatment done: stamp last_done_at and advance next_due_at by its RRULE.

    Non-recurring treatments have their reminder cleared (next_due_at -> None) so they leave the
    "due" lists; the completion still stamps last_done_at for history. Re-syncs the calendar.
    """
    now = timezone.now()
    obj.last_done_at = now
    obj.next_due_at = _next_occurrence(obj.recurrence_rule, now)
    obj.updated_by = acting_user
    obj.save()
    sync_event_for(obj)
    events.treatment_completed(obj.id, obj.household_id)
    return obj


def delete_treatment(acting_user: User, obj: PetTreatment) -> None:
    delete_event_for(obj)
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


# ---------------------------------------------------------------------------
# Appointments
# ---------------------------------------------------------------------------

_APPOINTMENT_FIELDS = {
    "pet_id", "title", "provider", "location", "start_at", "end_at", "notes", "visibility",
}


def create_appointment(acting_user: User, **data) -> PetAppointment:
    obj = PetAppointment(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    sync_event_for(obj)
    events.appointment_created(obj.id, obj.household_id)
    return obj


def update_appointment(acting_user: User, obj: PetAppointment, **data) -> PetAppointment:
    for key, val in data.items():
        if key in _APPOINTMENT_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    sync_event_for(obj)
    return obj


def delete_appointment(acting_user: User, obj: PetAppointment) -> None:
    delete_event_for(obj)
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()
