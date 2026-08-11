from datetime import datetime, time

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.notifications.services import create_notification
from apps.permissions.resolver import resolve_permission
from apps.scheduling.helpers import delete_event_for, sync_event_for
from apps.travel.models import BookingDeadline, TravelBooking, TravelIdea, Trip, TripImage


class TravelError(ValueError):
    pass


def _base(user):
    return {"household": get_active_household(), "created_by": user, "updated_by": user}


def _images(user, parent, rows):
    parent.images.all().delete()
    for position, data in enumerate(rows):
        if not data.get("image_url", "").strip():
            continue
        TripImage.objects.create(**_base(user), **{"trip": parent} if isinstance(parent, Trip) else {"idea": parent}, position=data.get("position", position), **{k: v for k, v in data.items() if k in {"image_url", "caption", "source_credit", "is_cover"}})


@transaction.atomic
def create_trip(user, *, participants=None, hidden_from_users=None, images=None, **data):
    obj = Trip.objects.create(**_base(user), **data)
    obj.participants.set(participants or [])
    obj.hidden_from_users.set([row for row in (hidden_from_users or []) if row.id != user.id])
    if images is not None:
        _images(user, obj, images)
    sync_event_for(obj)
    return obj


@transaction.atomic
def update_trip(user, obj, *, participants=None, hidden_from_users=None, images=None, **data):
    for field in {"title", "destination", "notes", "start_date", "end_date", "timezone", "status", "colour", "flights_required", "accommodation_required", "visibility"}:
        if field in data:
            setattr(obj, field, data[field])
    obj.updated_by = user
    obj.save()
    if participants is not None:
        obj.participants.set(participants)
    if hidden_from_users is not None:
        obj.hidden_from_users.set([row for row in hidden_from_users if row.id != user.id])
    if images is not None:
        _images(user, obj, images)
    sync_event_for(obj)
    for booking in obj.bookings.all():
        sync_event_for(booking)
        _sync_deadline(user, booking)
    return obj


def delete_trip(user, obj):
    delete_event_for(obj)
    for booking in obj.bookings.all():
        delete_event_for(booking)
        if hasattr(booking, "deadline"):
            delete_event_for(booking.deadline)
    obj.soft_delete()


def _notify_idea(user, idea):
    if idea.visibility != "household":
        return
    hidden_ids = set(idea.hidden_from_users.values_list("id", flat=True))
    for recipient in User.objects.filter(is_active=True).exclude(pk=user.pk).exclude(pk__in=hidden_ids):
        if resolve_permission(recipient, "view", "travel"):
            create_notification(recipient, title=f"New place to go: {idea.title}", message=f"{user.display_name} added {idea.destination}.", source_node="travel", action_url="/travel?tab=ideas")


@transaction.atomic
def create_idea(user, *, participants=None, hidden_from_users=None, images=None, **data):
    obj = TravelIdea.objects.create(**_base(user), **data)
    obj.participants.set(participants or [])
    obj.hidden_from_users.set([row for row in (hidden_from_users or []) if row.id != user.id])
    if images is not None:
        _images(user, obj, images)
    _notify_idea(user, obj)
    return obj


@transaction.atomic
def update_idea(user, obj, *, participants=None, hidden_from_users=None, images=None, **data):
    for field in {"title", "destination", "notes", "flights_required", "accommodation_required", "rough_cost", "currency", "colour", "status", "visibility"}:
        if field in data:
            setattr(obj, field, data[field])
    obj.updated_by = user
    obj.save()
    if participants is not None:
        obj.participants.set(participants)
    if hidden_from_users is not None:
        obj.hidden_from_users.set([row for row in hidden_from_users if row.id != user.id])
    if images is not None:
        _images(user, obj, images)
    return obj


def delete_idea(user, obj):
    obj.soft_delete()


@transaction.atomic
def convert_idea(user, idea):
    if idea.converted_trip_id:
        return idea.converted_trip
    trip = create_trip(user, title=idea.title, destination=idea.destination, notes=idea.notes,
        colour=idea.colour, flights_required=idea.flights_required,
        accommodation_required=idea.accommodation_required, visibility=idea.visibility,
        participants=list(idea.participants.all()), hidden_from_users=list(idea.hidden_from_users.all()), images=[{"image_url": row.image_url, "caption": row.caption, "source_credit": row.source_credit, "position": row.position, "is_cover": row.is_cover} for row in idea.images.all()])
    idea.status = TravelIdea.Status.CONVERTED
    idea.converted_trip = trip
    idea.updated_by = user
    idea.save()
    return trip


def _sync_deadline(user, booking):
    deadline = BookingDeadline.objects.filter(booking=booking).first()
    if not booking.book_by or booking.status in {TravelBooking.Status.BOOKED, TravelBooking.Status.CANCELLED}:
        if deadline:
            delete_event_for(deadline)
            deadline.delete()
        return
    due_at = timezone.make_aware(datetime.combine(booking.book_by, time.min), timezone.get_current_timezone())
    if deadline:
        deadline.due_at = due_at
        deadline.updated_by = user
        deadline.save()
    else:
        deadline = BookingDeadline.objects.create(booking=booking, due_at=due_at, **_base(user))
    sync_event_for(deadline)


@transaction.atomic
def create_booking(user, trip, **data):
    obj = TravelBooking.objects.create(trip=trip, **_base(user), **data)
    if obj.status == TravelBooking.Status.BOOKED:
        obj.booked_at = timezone.now(); obj.booked_by = user; obj.save()
    sync_event_for(obj)
    _sync_deadline(user, obj)
    return obj


@transaction.atomic
def update_booking(user, obj, **data):
    for field in {"kind", "title", "provider", "status", "quoted_amount", "booked_amount", "currency", "booking_reference", "url", "start_at", "end_at", "location", "flight_number", "departure_airport", "arrival_airport", "book_by", "notes", "colour"}:
        if field in data:
            setattr(obj, field, data[field])
    if obj.status == TravelBooking.Status.BOOKED and not obj.booked_at:
        obj.booked_at = timezone.now(); obj.booked_by = user
    elif obj.status != TravelBooking.Status.BOOKED:
        obj.booked_at = None; obj.booked_by = None
    obj.updated_by = user
    obj.save()
    sync_event_for(obj)
    _sync_deadline(user, obj)
    return obj


def delete_booking(user, obj):
    delete_event_for(obj)
    if hasattr(obj, "deadline"):
        delete_event_for(obj.deadline)
        obj.deadline.delete()
    obj.soft_delete()
