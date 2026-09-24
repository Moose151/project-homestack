"""The bounded set of records a User may restore straight after deleting one.

Every HouseholdBaseModel already soft-deletes and already has `restore()`; what was missing
was a way for the UI to offer that back. This registry is that way — one explicit entry per
record type, each delegating to a restore handler that inverts exactly what its node's delete
service did (a soft-delete plus, usually, dropping the Calendar projection).

This exists so routine deletion can stop asking "Are you sure?". Confirmation interrupts every
time, including the overwhelming majority of times the reader was right; undo interrupts nobody
and rescues the rest. It is deliberately *not* a general-purpose trash can: only record types
whose delete is cleanly invertible belong here, and a high-blast-radius delete (a whole list, a
pet, a person, a trip) keeps its confirmation instead.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class RestorableRecord:
    """One record type that can be un-deleted."""

    noun: str             # how the undo prompt names it: "assignment", "to-do"
    resource: str         # node key the caller must hold `delete` on
    load: Callable        # (pk) -> the soft-deleted instance, or None
    restore: Callable     # (acting_user, record) -> None


def _resync_calendar(record) -> None:
    """Put back the Calendar projection the delete removed (D7).

    Restoring the row alone would leave a dated record that exists everywhere except the
    household's timeline — present in its node, absent from Calendar and Hub.
    """
    from apps.scheduling.helpers import sync_event_for

    sync_event_for(record)


def _simple_dated_restore(record_cls, *, resource: str, noun: str) -> RestorableRecord:
    """Entry for a node whose delete is `delete_event_for()` + `soft_delete()`."""

    def _restore(acting_user, record):
        record.deleted_at = None
        record.updated_by = acting_user
        record.save(update_fields=["deleted_at", "updated_by", "updated_at"])
        _resync_calendar(record)

    return RestorableRecord(
        noun=noun,
        resource=resource,
        load=lambda pk: record_cls.all_objects.filter(
            pk=pk, deleted_at__isnull=False
        ).first(),
        restore=_restore,
    )


def _education_assessment():
    from apps.education.models import EducationAssessment

    return _simple_dated_restore(
        EducationAssessment, resource="education", noun="assignment"
    )


def _maintenance_task():
    from apps.homestead.models import MaintenanceTask

    return _simple_dated_restore(
        MaintenanceTask, resource="homestead", noun="maintenance task"
    )


def _pet_treatment():
    from apps.pets.models import PetTreatment

    return _simple_dated_restore(PetTreatment, resource="pets", noun="treatment")


def _pet_appointment():
    from apps.pets.models import PetAppointment

    return _simple_dated_restore(PetAppointment, resource="pets", noun="appointment")


def _atlas_list_item():
    from apps.atlas.models import AtlasListItem

    def _restore(acting_user, item):
        from apps.link_imports.models import LinkWatch

        item.deleted_at = None
        item.updated_by = acting_user
        item.save(update_fields=["deleted_at", "updated_by", "updated_at"])
        # Deleting the item soft-deleted its image and switched off any price watch; an undo
        # that silently dropped either would be a worse outcome than the delete it reverses.
        if item.image_attachment_id:
            attachment = item.image_attachment
            if attachment and attachment.deleted_at is not None:
                attachment.deleted_at = None
                attachment.updated_by = acting_user
                attachment.save(update_fields=["deleted_at", "updated_by", "updated_at"])
        LinkWatch.objects.filter(
            source_node="atlas", source_record_type="AtlasListItem", source_record_id=item.id,
        ).update(is_active=True, updated_by=acting_user)
        _resync_calendar(item)

    return RestorableRecord(
        noun="item",
        resource="atlas",
        load=lambda pk: AtlasListItem.all_objects.filter(
            pk=pk, deleted_at__isnull=False
        ).first(),
        restore=_restore,
    )


# Built lazily so importing core does not drag in every node app at startup.
_BUILDERS = {
    "AtlasListItem": _atlas_list_item,
    "EducationAssessment": _education_assessment,
    "MaintenanceTask": _maintenance_task,
    "PetAppointment": _pet_appointment,
    "PetTreatment": _pet_treatment,
}


def restorable_for(record_type: str) -> RestorableRecord | None:
    builder = _BUILDERS.get(record_type or "")
    return builder() if builder else None
