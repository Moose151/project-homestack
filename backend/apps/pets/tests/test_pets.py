"""Pets tests — Milestone 3 V1 slice. Permission tests first (D10).

Covers:
- Permissions across roles (unauthenticated/guest/user/child) on pets.
- CRUD for pets, treatments and appointments.
- Calendar sync: treatment next_due_at and appointment start_at create/update/delete a
  CalendarEvent via the scheduling helper (D7), tagged source_node = "pets".
- Complete treatment: stamps last_done_at and advances next_due_at by its RRULE (D8);
  non-recurring treatments have their reminder cleared.
- Visibility: a user's private pet is hidden from another user and from children.
- Search + Hub widgets.
"""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.pets.models import PetAppointment, PetTreatment
from apps.pets.services import (
    create_appointment,
    create_pet,
    create_treatment,
    complete_treatment,
    delete_treatment,
    update_treatment,
)
from apps.scheduling.models import CalendarEvent


def _make_user(username, role=User.Role.ADMIN, is_child=False) -> User:
    user = User.objects.create_user(
        username=username, display_name=username.capitalize(), role=role, password="pass123!"
    )
    user.set_pin("1234")
    if is_child:
        user.is_child_account = True
    user.save()
    return user


def _login(client, username, pin="1234"):
    client.post(
        reverse("auth-pin-login"),
        {"username": username, "pin": pin},
        content_type="application/json",
    )


def _future(hours=48):
    return timezone.now() + timezone.timedelta(hours=hours)


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

class PetsPermissionTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        self.user = _make_user("user", User.Role.USER)
        self.guest = _make_user("guest", User.Role.GUEST)
        self.child = _make_user("child", User.Role.USER, is_child=True)
        self.pet_url = reverse("pets-pet-list")

    def test_unauthenticated_rejected(self):
        self.assertIn(self.client.get(self.pet_url).status_code, [401, 403])

    def test_guest_can_view(self):
        _login(self.client, "guest")
        self.assertEqual(self.client.get(self.pet_url).status_code, 200)

    def test_guest_cannot_create(self):
        _login(self.client, "guest")
        resp = self.client.post(self.pet_url, {"name": "Rex"}, content_type="application/json")
        self.assertIn(resp.status_code, [401, 403])

    def test_user_can_create(self):
        _login(self.client, "user")
        resp = self.client.post(self.pet_url, {"name": "Rex", "species": "dog"}, content_type="application/json")
        self.assertEqual(resp.status_code, 201)

    def test_child_cannot_create(self):
        _login(self.client, "child")
        resp = self.client.post(self.pet_url, {"name": "Goldie"}, content_type="application/json")
        self.assertIn(resp.status_code, [401, 403])

    def test_user_cannot_delete(self):
        _login(self.client, "user")
        pet = create_pet(self.admin, name="Rex")
        resp = self.client.delete(reverse("pets-pet-detail", args=[pet.id]))
        self.assertIn(resp.status_code, [401, 403])

    def test_admin_can_delete(self):
        _login(self.client, "admin")
        pet = create_pet(self.admin, name="Rex")
        resp = self.client.delete(reverse("pets-pet-detail", args=[pet.id]))
        self.assertEqual(resp.status_code, 204)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

class PetsCrudTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        _login(self.client, "admin")

    def test_pet_crud(self):
        resp = self.client.post(
            reverse("pets-pet-list"),
            {"name": "Bella", "species": "cat", "microchip_number": "985..."},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        pet_id = resp.json()["id"]
        resp = self.client.patch(
            reverse("pets-pet-detail", args=[pet_id]),
            {"vet_name": "City Vets"}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["vet_name"], "City Vets")

    def test_treatment_crud_via_api(self):
        pet = create_pet(self.admin, name="Rex")
        resp = self.client.post(
            reverse("pets-treatment-list"),
            {"pet_id": pet.id, "treatment_type": "flea", "next_due_at": _future().isoformat()},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["treatment_type"], "flea")

    def test_appointment_start_required(self):
        pet = create_pet(self.admin, name="Rex")
        resp = self.client.post(
            reverse("pets-appointment-list"),
            {"pet_id": pet.id, "title": "Check-up"}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


# ---------------------------------------------------------------------------
# Calendar sync (D7)
# ---------------------------------------------------------------------------

class PetsCalendarSyncTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        self.pet = create_pet(self.admin, name="Rex")

    def test_treatment_due_creates_event(self):
        t = create_treatment(self.admin, pet_id=self.pet.id, treatment_type="worming", next_due_at=_future())
        t.refresh_from_db()
        self.assertIsNotNone(t.calendar_event_id)
        event = CalendarEvent.objects.get(pk=t.calendar_event_id)
        self.assertEqual(event.source_node.key, "pets")
        self.assertIn("Rex", event.title)

    def test_treatment_without_due_creates_no_event(self):
        t = create_treatment(self.admin, pet_id=self.pet.id, treatment_type="other")
        self.assertIsNone(t.calendar_event_id)

    def test_deleting_treatment_deletes_event(self):
        t = create_treatment(self.admin, pet_id=self.pet.id, treatment_type="flea", next_due_at=_future())
        event_id = t.calendar_event_id
        delete_treatment(self.admin, t)
        self.assertFalse(CalendarEvent.objects.filter(pk=event_id).exists())

    def test_appointment_creates_event(self):
        a = create_appointment(self.admin, pet_id=self.pet.id, title="Check-up", start_at=_future())
        a.refresh_from_db()
        self.assertIsNotNone(a.calendar_event_id)
        self.assertEqual(CalendarEvent.objects.get(pk=a.calendar_event_id).source_node.key, "pets")


# ---------------------------------------------------------------------------
# Complete treatment (RRULE advance, D8)
# ---------------------------------------------------------------------------

class PetsCompleteTreatmentTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        self.pet = create_pet(self.admin, name="Rex")

    def test_recurring_treatment_advances_next_due(self):
        past_due = timezone.now() - timezone.timedelta(days=1)
        t = create_treatment(
            self.admin, pet_id=self.pet.id, treatment_type="flea",
            next_due_at=past_due, recurrence_rule="FREQ=WEEKLY",
        )
        completed = complete_treatment(self.admin, t)
        self.assertIsNotNone(completed.last_done_at)
        self.assertIsNotNone(completed.next_due_at)
        self.assertGreater(completed.next_due_at, timezone.now())  # advanced into the future

    def test_non_recurring_treatment_clears_reminder(self):
        t = create_treatment(self.admin, pet_id=self.pet.id, treatment_type="vaccination", next_due_at=_future())
        completed = complete_treatment(self.admin, t)
        self.assertIsNotNone(completed.last_done_at)
        self.assertIsNone(completed.next_due_at)

    def test_complete_via_api(self):
        _login(self.client, "admin")
        t = create_treatment(self.admin, pet_id=self.pet.id, treatment_type="grooming", next_due_at=_future())
        resp = self.client.post(reverse("pets-treatment-complete", args=[t.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.json()["last_done_at"])


# ---------------------------------------------------------------------------
# Visibility (D10)
# ---------------------------------------------------------------------------

class PetsVisibilityTests(TestCase):
    def setUp(self):
        self.owner = _make_user("owner", User.Role.USER)
        self.other = _make_user("other", User.Role.USER)
        self.child = _make_user("child", User.Role.USER, is_child=True)
        create_pet(self.owner, name="Secret pet", visibility="private")

    def test_owner_sees_own_private_pet(self):
        from apps.pets.selectors import list_pets
        self.assertIn("Secret pet", [p.name for p in list_pets(self.owner)])

    def test_other_user_cannot_see_private_pet(self):
        from apps.pets.selectors import list_pets
        self.assertNotIn("Secret pet", [p.name for p in list_pets(self.other)])

    def test_child_cannot_see_private_pet(self):
        from apps.pets.selectors import list_pets
        self.assertNotIn("Secret pet", [p.name for p in list_pets(self.child)])


# ---------------------------------------------------------------------------
# Search + Hub widgets
# ---------------------------------------------------------------------------

class PetsSearchAndHubTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        _login(self.client, "admin")

    def test_search_matches_pets_and_treatments(self):
        pet = create_pet(self.admin, name="Rex", breed="Labrador")
        create_treatment(self.admin, pet_id=pet.id, treatment_type="flea", name="Frontline")
        resp = self.client.get(reverse("pets-search"), {"q": "Frontline"})
        self.assertEqual([t["name"] for t in resp.json()["treatments"]], ["Frontline"])
        resp = self.client.get(reverse("pets-search"), {"q": "Labrador"})
        self.assertEqual([p["name"] for p in resp.json()["pets"]], ["Rex"])

    def test_reminders_widget_lists_due(self):
        from apps.hub.services import _pets_widget_content
        pet = create_pet(self.admin, name="Rex")
        create_treatment(self.admin, pet_id=pet.id, treatment_type="worming", next_due_at=_future())
        content = _pets_widget_content("pets_reminders", self.admin)
        self.assertEqual(len(content), 1)

    def test_appointments_widget_lists_upcoming(self):
        from apps.hub.services import _pets_widget_content
        pet = create_pet(self.admin, name="Rex")
        create_appointment(self.admin, pet_id=pet.id, title="Check-up", start_at=_future())
        create_appointment(self.admin, pet_id=pet.id, title="Old", start_at=timezone.now() - timezone.timedelta(days=2))
        content = _pets_widget_content("pets_appointments", self.admin)
        self.assertEqual([a["title"] for a in content], ["Check-up"])
