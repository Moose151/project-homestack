from collections import defaultdict

from rest_framework import serializers

from apps.accounts.models import User
from apps.people.models import Person
from apps.travel.models import BookingDeadline, TravelBooking, TravelIdea, Trip, TripImage


class TripImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TripImage
        fields = ["id", "image_url", "caption", "source_credit", "position", "is_cover"]
        read_only_fields = ["id"]


class BookingSerializer(serializers.ModelSerializer):
    deadline_calendar_event_id = serializers.SerializerMethodField()

    class Meta:
        model = TravelBooking
        fields = [
            "id", "trip_id", "kind", "title", "provider", "status", "quoted_amount",
            "booked_amount", "currency", "booking_reference", "url", "start_at", "end_at",
            "location", "flight_number", "departure_airport", "arrival_airport", "book_by",
            "booked_at", "booked_by_id", "notes", "colour", "calendar_event_id",
            "deadline_calendar_event_id", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "trip_id", "booked_at", "booked_by_id", "calendar_event_id", "deadline_calendar_event_id", "created_at", "updated_at"]

    def get_deadline_calendar_event_id(self, obj):
        try:
            return obj.deadline.calendar_event_id
        except BookingDeadline.DoesNotExist:
            return None

    def validate(self, attrs):
        start = attrs.get("start_at", getattr(self.instance, "start_at", None))
        end = attrs.get("end_at", getattr(self.instance, "end_at", None))
        if start and end and end < start:
            raise serializers.ValidationError({"end_at": "End time cannot be before start time."})
        return attrs


class TripSerializer(serializers.ModelSerializer):
    participant_ids = serializers.PrimaryKeyRelatedField(source="participants", queryset=Person.objects.all(), many=True, required=False)
    hidden_from_user_ids = serializers.PrimaryKeyRelatedField(source="hidden_from_users", queryset=User.objects.all(), many=True, required=False)
    images = TripImageSerializer(many=True, required=False)
    bookings = BookingSerializer(many=True, read_only=True)
    cost_summary = serializers.SerializerMethodField()
    booking_progress = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            "id", "title", "destination", "notes", "start_date", "end_date", "timezone",
            "status", "colour", "flights_required", "accommodation_required", "visibility",
            "participant_ids", "hidden_from_user_ids", "images", "bookings", "cost_summary", "booking_progress",
            "calendar_event_id", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "bookings", "cost_summary", "booking_progress", "calendar_event_id", "created_at", "updated_at"]

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": "End date cannot be before start date."})
        return attrs

    def get_cost_summary(self, obj):
        totals = defaultdict(lambda: {"quoted": 0, "booked": 0})
        for row in obj.bookings.all():
            if row.status == TravelBooking.Status.CANCELLED:
                continue
            totals[row.currency]["quoted"] += row.quoted_amount or 0
            booked_value = row.booked_amount
            if booked_value is None:
                booked_value = (row.quoted_amount or 0) if row.status == TravelBooking.Status.BOOKED else 0
            totals[row.currency]["booked"] += booked_value
        return [{"currency": currency, "quoted": str(values["quoted"]), "booked": str(values["booked"])} for currency, values in sorted(totals.items())]

    def get_booking_progress(self, obj):
        required = []
        if obj.flights_required:
            required.append(TravelBooking.Kind.FLIGHT)
        if obj.accommodation_required:
            required.append(TravelBooking.Kind.ACCOMMODATION)
        rows = [row for row in obj.bookings.all() if row.status != TravelBooking.Status.CANCELLED]
        return {
            "required_types": required,
            "booked_required_types": [kind for kind in required if any(row.kind == kind and row.status == TravelBooking.Status.BOOKED for row in rows)],
            "component_count": len(rows), "booked_count": sum(row.status == TravelBooking.Status.BOOKED for row in rows),
        }


class TravelIdeaSerializer(serializers.ModelSerializer):
    participant_ids = serializers.PrimaryKeyRelatedField(source="participants", queryset=Person.objects.all(), many=True, required=False)
    hidden_from_user_ids = serializers.PrimaryKeyRelatedField(source="hidden_from_users", queryset=User.objects.all(), many=True, required=False)
    images = TripImageSerializer(many=True, required=False)

    class Meta:
        model = TravelIdea
        fields = [
            "id", "title", "destination", "notes", "flights_required", "accommodation_required",
            "rough_cost", "currency", "colour", "status", "visibility", "participant_ids",
            "hidden_from_user_ids", "images", "converted_trip_id", "created_by_id", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "converted_trip_id", "created_by_id", "created_at", "updated_at"]
