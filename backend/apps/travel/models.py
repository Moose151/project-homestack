from datetime import datetime, time, timedelta

from django.db import models
from django.utils import timezone

from apps.core.models import HouseholdBaseModel
from apps.scheduling.mixins import CalendarSyncMixin


class Visibility(models.TextChoices):
    PRIVATE = "private", "Private"
    HOUSEHOLD = "household", "Household"
    ROLE_RESTRICTED = "role_restricted", "Role restricted"


def _aware(day, at=time.min):
    return timezone.make_aware(datetime.combine(day, at), timezone.get_current_timezone())


class Trip(CalendarSyncMixin, HouseholdBaseModel):
    class Status(models.TextChoices):
        PLANNING = "planning", "Planning"
        READY = "ready_to_book", "Ready to book"
        BOOKED = "booked", "Booked"
        TRAVELLING = "travelling", "Travelling"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    title = models.CharField(max_length=200)
    destination = models.CharField(max_length=255)
    notes = models.TextField(blank=True, default="")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    timezone = models.CharField(max_length=64, blank=True, default="Australia/Brisbane")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNING)
    colour = models.CharField(max_length=7, default="#2B7FD0")
    flights_required = models.BooleanField(default=False)
    accommodation_required = models.BooleanField(default=False)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD)
    participants = models.ManyToManyField("people.Person", blank=True, related_name="travel_trips")
    hidden_from_users = models.ManyToManyField("accounts.User", blank=True, related_name="hidden_trips")
    calendar_event_id = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["start_date", "title"]

    def get_calendar_node_key(self):
        return "travel"

    def get_calendar_data(self):
        if not self.start_date or self.status == self.Status.CANCELLED:
            return None
        marker = "✓ Booked" if self.status in {self.Status.BOOKED, self.Status.TRAVELLING, self.Status.COMPLETED} else "○ Planned"
        return {
            "title": f"{marker} · {self.title}", "description": self.destination,
            "start_at": _aware(self.start_date),
            "end_at": _aware((self.end_date or self.start_date) + timedelta(days=1)),
            "is_all_day": True, "colour": self.colour, "visibility": self.visibility,
            "assigned_to_person_ids": list(self.participants.values_list("id", flat=True)),
            "hidden_from_user_ids": list(self.hidden_from_users.values_list("id", flat=True)),
        }


class TravelIdea(HouseholdBaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CONVERTED = "converted", "Converted"
        ARCHIVED = "archived", "Archived"

    title = models.CharField(max_length=200)
    destination = models.CharField(max_length=255)
    notes = models.TextField(blank=True, default="")
    flights_required = models.BooleanField(default=False)
    accommodation_required = models.BooleanField(default=False)
    rough_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="AUD")
    colour = models.CharField(max_length=7, default="#2B7FD0")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD)
    participants = models.ManyToManyField("people.Person", blank=True, related_name="travel_ideas")
    hidden_from_users = models.ManyToManyField("accounts.User", blank=True, related_name="hidden_travel_ideas")
    converted_trip = models.OneToOneField(Trip, null=True, blank=True, on_delete=models.SET_NULL, related_name="source_idea")

    class Meta:
        ordering = ["-created_at"]


class TripImage(HouseholdBaseModel):
    trip = models.ForeignKey(Trip, null=True, blank=True, on_delete=models.CASCADE, related_name="images")
    idea = models.ForeignKey(TravelIdea, null=True, blank=True, on_delete=models.CASCADE, related_name="images")
    image_url = models.CharField(max_length=1000)
    caption = models.CharField(max_length=255, blank=True, default="")
    source_credit = models.CharField(max_length=255, blank=True, default="")
    position = models.PositiveSmallIntegerField(default=0)
    is_cover = models.BooleanField(default=False)

    class Meta:
        ordering = ["position", "id"]
        constraints = [models.CheckConstraint(
            check=(models.Q(trip__isnull=False, idea__isnull=True) | models.Q(trip__isnull=True, idea__isnull=False)),
            name="travel_image_exactly_one_parent",
        )]


class TravelBooking(CalendarSyncMixin, HouseholdBaseModel):
    class Kind(models.TextChoices):
        FLIGHT = "flight", "Flight"
        ACCOMMODATION = "accommodation", "Accommodation"
        TRANSPORT = "transport", "Transport"
        ACTIVITY = "activity", "Activity"
        RESTAURANT = "restaurant", "Restaurant"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        RESEARCHING = "researching", "Researching"
        PLANNED = "planned", "Planned"
        BOOKED = "booked", "Booked"
        CANCELLED = "cancelled", "Cancelled"

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="bookings")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    title = models.CharField(max_length=200)
    provider = models.CharField(max_length=160, blank=True, default="")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PLANNED)
    quoted_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    booked_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="AUD")
    booking_reference = models.CharField(max_length=160, blank=True, default="")
    url = models.CharField(max_length=1000, blank=True, default="")
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True, default="")
    flight_number = models.CharField(max_length=40, blank=True, default="")
    departure_airport = models.CharField(max_length=120, blank=True, default="")
    arrival_airport = models.CharField(max_length=120, blank=True, default="")
    book_by = models.DateField(null=True, blank=True)
    booked_at = models.DateTimeField(null=True, blank=True)
    booked_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="travel_bookings_made")
    notes = models.TextField(blank=True, default="")
    colour = models.CharField(max_length=7, blank=True, default="")
    calendar_event_id = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["start_at", "id"]

    def get_calendar_node_key(self):
        return "travel"

    def get_calendar_data(self):
        if not self.start_at or self.status == self.Status.CANCELLED:
            return None
        marker = "✓" if self.status == self.Status.BOOKED else "○"
        return {
            "title": f"{marker} {self.trip.title} · {self.title}", "description": self.notes,
            "start_at": self.start_at, "end_at": self.end_at, "location": self.location,
            "colour": self.colour or self.trip.colour, "visibility": self.trip.visibility,
            "assigned_to_person_ids": list(self.trip.participants.values_list("id", flat=True)),
            "hidden_from_user_ids": list(self.trip.hidden_from_users.values_list("id", flat=True)),
        }


class BookingDeadline(CalendarSyncMixin, HouseholdBaseModel):
    booking = models.OneToOneField(TravelBooking, on_delete=models.CASCADE, related_name="deadline")
    due_at = models.DateTimeField()
    calendar_event_id = models.PositiveBigIntegerField(null=True, blank=True)

    def get_calendar_node_key(self):
        return "travel"

    def get_calendar_data(self):
        if self.booking.status in {TravelBooking.Status.BOOKED, TravelBooking.Status.CANCELLED}:
            return None
        return {
            "title": f"{self.booking.trip.title} · Book {self.booking.title}",
            "start_at": self.due_at, "is_all_day": True, "event_kind": "task",
            "description": f"{self.booking.get_kind_display()} booking deadline",
            "colour": self.booking.colour or self.booking.trip.colour,
            "visibility": self.booking.trip.visibility,
            "assigned_to_person_ids": list(self.booking.trip.participants.values_list("id", flat=True)),
            "hidden_from_user_ids": list(self.booking.trip.hidden_from_users.values_list("id", flat=True)),
        }
