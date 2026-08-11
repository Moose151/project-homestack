from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.notifications.models import Notification
from apps.nodes.models import HouseholdNode
from apps.people.models import Person
from apps.scheduling.models import CalendarEvent
from apps.travel.models import TravelIdea, Trip


class TravelFlowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("traveladmin", "Travel Admin", password="pw", role="admin")
        self.other = User.objects.create_user("traveller", "Traveller", password="pw", role="user")
        # Explicit surprise exclusions also apply to elevated household roles.
        self.surprise = User.objects.create_user("surprise", "Surprise", password="pw", role="manager")
        household = get_active_household()
        HouseholdNode.objects.filter(household=household, node__key="travel").update(is_enabled=True)
        self.admin_person = Person.objects.create(household=household, linked_user=self.admin, display_name="Admin", created_by=self.admin, updated_by=self.admin)
        self.other_person = Person.objects.create(household=household, linked_user=self.other, display_name="Traveller", created_by=self.admin, updated_by=self.admin)
        self.client.force_login(self.admin)

    def test_trip_images_people_dates_and_surprise_visibility(self):
        response = self.client.post("/api/v1/travel/trips/", {
            "title": "Secret Fiji", "destination": "Fiji",
            "start_date": "2027-01-10", "end_date": "2027-01-17", "colour": "#e0564a",
            "participant_ids": [self.admin_person.id, self.other_person.id],
            "hidden_from_user_ids": [self.surprise.id],
            "images": [{"image_url": "https://images.example/fiji.jpg", "is_cover": True}],
        }, content_type="application/json")
        self.assertEqual(response.status_code, 201, response.data)
        trip = Trip.objects.get(pk=response.data["id"])
        self.assertEqual(trip.images.count(), 1)
        event = CalendarEvent.objects.get(pk=trip.calendar_event_id)
        self.assertEqual(event.colour, "#e0564a")
        self.assertIn("Planned", event.title)
        self.assertTrue(event.hidden_from_users.filter(pk=self.surprise.id).exists())
        self.client.force_login(self.surprise)
        self.assertEqual(self.client.get("/api/v1/travel/trips/").json(), [])
        self.assertNotIn(event.id, [row["id"] for row in self.client.get("/api/v1/calendar/events/").json()])
        self.assertEqual(self.client.get(f"/api/v1/calendar/events/{event.id}/").status_code, 404)

    def test_idea_notification_corner_activity_and_idempotent_conversion(self):
        response = self.client.post("/api/v1/travel/ideas/", {
            "title": "See the snow", "destination": "Japan", "flights_required": True,
            "images": [{"image_url": "https://images.example/japan.jpg"}],
        }, content_type="application/json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(Notification.objects.filter(recipient_user=self.other, source_node="travel").exists())
        corner = self.client.get(f"/api/v1/corners/{self.admin_person.id}/").json()
        self.assertTrue(any(row["source_node"] == "travel" and "See the snow" in row["title"] for row in corner["activity"]))
        first = self.client.post(f"/api/v1/travel/ideas/{response.data['id']}/convert/").json()
        second = self.client.post(f"/api/v1/travel/ideas/{response.data['id']}/convert/").json()
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(Trip.objects.filter(source_idea__id=response.data["id"]).count(), 1)
        self.assertEqual(first["images"][0]["image_url"], "https://images.example/japan.jpg")

    def test_separate_booking_deadlines_name_trip_and_component_and_roll_up_costs(self):
        trip = self.client.post("/api/v1/travel/trips/", {
            "title": "Japan 2027", "destination": "Tokyo", "flights_required": True,
            "accommodation_required": True,
        }, content_type="application/json").json()
        book_by = (timezone.localdate() + timedelta(days=10)).isoformat()
        flight = self.client.post(f"/api/v1/travel/trips/{trip['id']}/bookings/", {
            "kind": "flight", "title": "Outbound flights", "quoted_amount": "2400.00",
            "book_by": book_by, "start_at": (timezone.now() + timedelta(days=50)).isoformat(),
        }, content_type="application/json")
        stay = self.client.post(f"/api/v1/travel/trips/{trip['id']}/bookings/", {
            "kind": "accommodation", "title": "Tokyo hotel", "quoted_amount": "1800.00",
            "book_by": (timezone.localdate() + timedelta(days=14)).isoformat(),
        }, content_type="application/json")
        self.assertEqual(flight.status_code, 201, flight.data)
        self.assertEqual(stay.status_code, 201, stay.data)
        deadline = CalendarEvent.objects.get(pk=flight.data["deadline_calendar_event_id"])
        self.assertEqual(deadline.title, "Japan 2027 · Book Outbound flights")
        detail = self.client.get(f"/api/v1/travel/trips/{trip['id']}/").json()
        self.assertEqual(detail["cost_summary"][0]["quoted"], "4200.00")
        self.client.patch(f"/api/v1/travel/bookings/{flight.data['id']}/", {
            "status": "booked", "booked_amount": "2300.00",
        }, content_type="application/json")
        self.assertFalse(CalendarEvent.objects.filter(pk=deadline.id).exists())
