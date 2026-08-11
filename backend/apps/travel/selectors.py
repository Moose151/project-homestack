from apps.permissions.visibility import apply_visibility
from apps.travel.models import TravelIdea, Trip, TravelBooking


def list_trips(user):
    return list(apply_visibility(Trip.objects.prefetch_related("participants", "images", "bookings"), user))


def get_trip(user, pk):
    return apply_visibility(Trip.objects.prefetch_related("participants", "images", "bookings"), user).filter(pk=pk).first()


def list_ideas(user):
    return list(apply_visibility(TravelIdea.objects.prefetch_related("participants", "images"), user))


def get_idea(user, pk):
    return apply_visibility(TravelIdea.objects.prefetch_related("participants", "images"), user).filter(pk=pk).first()


def get_booking(user, pk):
    visible_trip_ids = apply_visibility(Trip.objects.all(), user).values_list("id", flat=True)
    return TravelBooking.objects.select_related("trip").filter(pk=pk, trip_id__in=visible_trip_ids).first()
