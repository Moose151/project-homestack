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

Deliberately absent, with reasons, so the next person does not have to re-derive them:

- **BookClubBook** — `delete_club_book()` hard-deletes the club's queue rows for that book
  (a queryset `.delete()`, which this project's soft-delete manager does not intercept), so a
  restore would put the book back on the shelf while silently dropping its place in the up-next
  queue. A half-restore is a worse outcome than the delete it reverses.
- **Bill, BudgetBucket, FinanceCategory, AtlasList, Trip, WikiCategory, BookClub** — each takes
  other records with it, or moves them somewhere else. There the pause is the point.
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
    # Set when the owning node gates access behind re-authentication (apps/nodes/access.py).
    # Undo must pass the same gate the delete did: a locked node stays locked for the
    # inverse of an operation it would not have allowed in the first place, and the access is
    # audited the same way. Without this, the central restore endpoint would be the one door
    # into a sensitive node that neither locks nor leaves a record.
    sensitive_node: str = ""


def _resync_calendar(record) -> None:
    """Put back the Calendar projection the delete removed (D7).

    Restoring the row alone would leave a dated record that exists everywhere except the
    household's timeline — present in its node, absent from Calendar and Hub.
    """
    from apps.scheduling.helpers import sync_event_for

    sync_event_for(record)


def _entry(
    record_cls,
    *,
    resource: str,
    noun: str,
    calendar: bool = False,
    sensitive_node: str = "",
    after: Callable | None = None,
) -> RestorableRecord:
    """Build an entry for a node whose delete is `soft_delete()` plus known side effects.

    `calendar` re-syncs the Calendar projection a `delete_event_for()` removed; `after` runs
    anything else that delete did and this has to undo.
    """

    def _restore(acting_user, record):
        record.deleted_at = None
        record.updated_by = acting_user
        record.save(update_fields=["deleted_at", "updated_by", "updated_at"])
        if calendar:
            _resync_calendar(record)
        if after is not None:
            after(acting_user, record)

    return RestorableRecord(
        noun=noun,
        resource=resource,
        load=lambda pk: record_cls.all_objects.filter(
            pk=pk, deleted_at__isnull=False
        ).first(),
        restore=_restore,
        sensitive_node=sensitive_node,
    )


# ---------------------------------------------------------------------------
# Atlas
# ---------------------------------------------------------------------------

def _atlas_list_item():
    from apps.atlas.models import AtlasListItem

    def _after(acting_user, item):
        from apps.link_imports.models import LinkWatch

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

    return _entry(AtlasListItem, resource="atlas", noun="item", calendar=True, after=_after)


def _atlas_note():
    from apps.atlas.models import AtlasNote

    return _entry(AtlasNote, resource="atlas", noun="note")


def _atlas_contact():
    from apps.atlas.models import AtlasContact

    # Birthdays are derived from the contact row on read rather than projected into a
    # CalendarEvent, so putting the row back is all a Calendar birthday needs.
    return _entry(AtlasContact, resource="atlas", noun="person")


# ---------------------------------------------------------------------------
# Education, Homestead, Pets
# ---------------------------------------------------------------------------

def _education_assessment():
    from apps.education.models import EducationAssessment

    return _entry(
        EducationAssessment, resource="education", noun="assignment", calendar=True
    )


def _maintenance_task():
    from apps.homestead.models import MaintenanceTask

    return _entry(MaintenanceTask, resource="homestead", noun="maintenance task", calendar=True)


def _pet_treatment():
    from apps.pets.models import PetTreatment

    return _entry(PetTreatment, resource="pets", noun="treatment", calendar=True)


def _pet_appointment():
    from apps.pets.models import PetAppointment

    return _entry(PetAppointment, resource="pets", noun="appointment", calendar=True)


# ---------------------------------------------------------------------------
# Home Wiki
# ---------------------------------------------------------------------------

def _wiki_page():
    from apps.home_wiki import events
    from apps.home_wiki.models import WikiPage

    def _after(_acting_user, page):
        # `delete_page()` announced the page's disappearance on the bus (D4). Consumers are
        # wired in a later slice, but an announcement that is never taken back would leave
        # them permanently wrong about a page that exists again.
        events.page_created(page.id, page.household_id)

    # `homewiki`, not the `home_wiki` app/node key: the permission resource has no underscore
    # (apps/home_wiki/views.py uses the same string), and a resource nobody holds would refuse
    # every restore.
    return _entry(WikiPage, resource="homewiki", noun="page", after=_after)


# ---------------------------------------------------------------------------
# Travel
# ---------------------------------------------------------------------------

def _travel_idea():
    from apps.travel.models import TravelIdea

    return _entry(TravelIdea, resource="travel", noun="idea")


def _travel_itinerary_item():
    from apps.travel.models import TravelItineraryItem

    return _entry(TravelItineraryItem, resource="travel", noun="plan", calendar=True)


def _travel_booking():
    from apps.travel.models import TravelBooking

    def _after(acting_user, booking):
        from apps.travel import services

        # Deleting a booking also hard-deleted its "book by" deadline row, so there is nothing
        # to un-delete — it has to be made again. `update_booking` with no changes is the
        # node's own path for exactly that: it re-derives the deadline from `book_by` and
        # re-syncs both Calendar projections, so the deadline comes back the way the node
        # would have created it rather than the way this file guesses it should look.
        services.update_booking(acting_user, booking)

    return _entry(TravelBooking, resource="travel", noun="booking", after=_after)


# ---------------------------------------------------------------------------
# Books
# ---------------------------------------------------------------------------

def _personal_book_entry():
    from apps.books.models import PersonalBookEntry

    return _entry(PersonalBookEntry, resource="books", noun="book")


# ---------------------------------------------------------------------------
# Solace — every entry carries the node's re-authentication gate (see above).
# ---------------------------------------------------------------------------

def _planned_purchase():
    from apps.solace.models import PlannedPurchase

    return _entry(
        PlannedPurchase, resource="solace", noun="purchase",
        calendar=True, sensitive_node="solace",
    )


def _payday():
    from apps.solace.models import Payday

    return _entry(
        Payday, resource="solace", noun="payday", calendar=True, sensitive_node="solace",
    )


def _bucket_entry():
    from apps.solace.models import BucketEntry

    def _after(acting_user, entry):
        from decimal import Decimal

        from apps.solace.models import BudgetBucket

        # Deleting the entry took its amount back out of the bucket balance, so a restore that
        # only revived the row would leave the bucket saying one thing and its entries another.
        # Locked exactly as `delete_bucket_entry()` locks it: this is money, and two undos
        # racing must not both add the amount.
        locked = BudgetBucket.objects.select_for_update().get(pk=entry.bucket_id)
        locked.current_amount = Decimal(locked.current_amount) + entry.signed_amount
        locked.updated_by = acting_user
        locked.save(update_fields=["current_amount", "updated_by", "updated_at"])

    return _entry(
        BucketEntry, resource="solace", noun="entry", sensitive_node="solace", after=_after,
    )


def _balance_snapshot():
    from apps.solace.models import AccountBalanceSnapshot

    return _entry(
        AccountBalanceSnapshot, resource="solace", noun="snapshot", sensitive_node="solace",
    )


# Built lazily so importing core does not drag in every node app at startup.
_BUILDERS = {
    "AccountBalanceSnapshot": _balance_snapshot,
    "AtlasContact": _atlas_contact,
    "AtlasListItem": _atlas_list_item,
    "AtlasNote": _atlas_note,
    "BucketEntry": _bucket_entry,
    "EducationAssessment": _education_assessment,
    "MaintenanceTask": _maintenance_task,
    "Payday": _payday,
    "PersonalBookEntry": _personal_book_entry,
    "PetAppointment": _pet_appointment,
    "PetTreatment": _pet_treatment,
    "PlannedPurchase": _planned_purchase,
    "TravelBooking": _travel_booking,
    "TravelIdea": _travel_idea,
    "TravelItineraryItem": _travel_itinerary_item,
    "WikiPage": _wiki_page,
}


def restorable_for(record_type: str) -> RestorableRecord | None:
    builder = _BUILDERS.get(record_type or "")
    return builder() if builder else None
