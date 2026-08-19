"""Atlas tests — Phase 1.8. Tests written first per D10.

Covers:
- Notes: permissions (unauthenticated/guest/user/manager), CRUD, FTS search.
- Lists + items: CRUD, complete/uncomplete.
- Reminders: permissions, CRUD, calendar sync (create/update/delete keeps event in sync).
- Visibility mixin: child sees only 'household', user sees own 'private'.
"""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.atlas.models import AtlasList, AtlasNote, AtlasReminder
from apps.people.models import Person
from apps.atlas.services import (
    create_atlas_list,
    create_list_item,
    create_note,
    create_reminder,
    delete_reminder,
    update_reminder,
)
from apps.scheduling.models import CalendarEvent
from apps.core.models import get_active_household


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(username, role=User.Role.ADMIN, is_child=False) -> User:
    user = User.objects.create_user(
        username=username, display_name=username.capitalize(), role=role, password="pass123!"
    )
    user.set_pin("1234")
    if is_child:
        user.is_child_account = True
        user.save()
    else:
        user.save()
    return user


def _login(client, username, pin="1234"):
    client.post(
        reverse("auth-pin-login"),
        {"username": username, "pin": pin},
        content_type="application/json",
    )


def _future(hours=24):
    return timezone.now() + timezone.timedelta(hours=hours)


class DailyCoordinationTests(TestCase):
    def setUp(self):
        self.admin = _make_user("coordadmin")
        _login(self.client, "coordadmin")

    def test_dated_list_item_syncs_and_completion_removes_calendar_mirror(self):
        atlas_list = create_atlas_list(self.admin, title="Jobs", list_type="todo")
        item = create_list_item(self.admin, atlas_list, title="Call plumber", due_at=_future())
        item.refresh_from_db()
        self.assertIsNotNone(item.calendar_event_id)
        event = CalendarEvent.objects.get(pk=item.calendar_event_id)
        self.assertEqual(event.event_kind, "task")
        response = self.client.post(f"/api/v1/atlas/lists/{atlas_list.id}/items/{item.id}/complete/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CalendarEvent.objects.filter(pk=event.id).exists())

    def test_external_and_household_birthdays_are_projected_without_duplication(self):
        person = Person.objects.create(
            household=get_active_household(), linked_user=self.admin, display_name="Alex",
            date_of_birth=timezone.datetime(1990, 8, 12).date(), created_by=self.admin, updated_by=self.admin,
        )
        response = self.client.post("/api/v1/atlas/contacts/", {
            "name": "Jamie", "date_of_birth": "1985-08-13", "relationship": "Friend",
        }, content_type="application/json")
        self.assertEqual(response.status_code, 201, response.data)
        birthdays = self.client.get("/api/v1/atlas/birthday-occurrences/?start=2026-08-11&end=2026-08-15").json()
        self.assertEqual([row["title"] for row in birthdays], ["Alex turns 36", "Jamie turns 41"])
        self.assertEqual(sum(row["person_id"] == person.id for row in birthdays), 1)

    def test_pet_birthday_shows_turning_age_and_deep_link_id(self):
        from apps.pets.models import Pet
        pet = Pet.objects.create(
            household=get_active_household(), name="Buddy",
            date_of_birth=timezone.datetime(2020, 8, 20).date(),
            created_by=self.admin, updated_by=self.admin,
        )
        rows = self.client.get("/api/v1/atlas/birthday-occurrences/?start=2026-08-19&end=2026-08-21").json()
        pet_rows = [row for row in rows if row["pet_id"] == pet.id]
        self.assertEqual(len(pet_rows), 1)
        self.assertEqual(pet_rows[0]["title"], "Buddy's 6th Birthday")
        self.assertEqual(pet_rows[0]["age"], 6)
        self.assertEqual(pet_rows[0]["date"], "2026-08-20")

    def test_pet_leap_day_birthday_lands_on_feb_28_in_non_leap_years(self):
        from apps.pets.models import Pet
        pet = Pet.objects.create(
            household=get_active_household(), name="Frog", species="reptile",
            date_of_birth=timezone.datetime(2020, 2, 29).date(),
            created_by=self.admin, updated_by=self.admin,
        )
        rows = self.client.get("/api/v1/atlas/birthday-occurrences/?start=2027-02-27&end=2027-03-01").json()
        pet_rows = [row for row in rows if row["pet_id"] == pet.id]
        self.assertEqual([row["date"] for row in pet_rows], ["2027-02-28"])

    def test_removing_pet_dob_removes_generated_birthday(self):
        from apps.pets.models import Pet
        pet = Pet.objects.create(
            household=get_active_household(), name="Milo",
            date_of_birth=timezone.datetime(2019, 8, 20).date(),
            created_by=self.admin, updated_by=self.admin,
        )
        window = "/api/v1/atlas/birthday-occurrences/?start=2026-08-19&end=2026-08-21"
        before = self.client.get(window).json()
        self.assertTrue(any(row["pet_id"] == pet.id for row in before))
        pet.date_of_birth = None
        pet.save(update_fields=["date_of_birth"])
        after = self.client.get(window).json()
        self.assertFalse(any(row["pet_id"] == pet.id for row in after))


# ---------------------------------------------------------------------------
# Notes permission tests
# ---------------------------------------------------------------------------

class NotePermissionTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        self.manager = _make_user("manager", User.Role.MANAGER)
        self.user = _make_user("user", User.Role.USER)
        self.guest = _make_user("guest", User.Role.GUEST)
        self.child = _make_user("child", User.Role.USER, is_child=True)
        self.list_url = reverse("atlas-note-list")

    def test_unauthenticated_rejected(self):
        self.assertIn(self.client.get(self.list_url).status_code, [401, 403])

    def test_guest_can_view(self):
        _login(self.client, "guest")
        self.assertEqual(self.client.get(self.list_url).status_code, 200)

    def test_guest_cannot_create(self):
        _login(self.client, "guest")
        resp = self.client.post(self.list_url, {"title": "x"}, content_type="application/json")
        self.assertIn(resp.status_code, [401, 403])

    def test_user_can_create(self):
        _login(self.client, "user")
        resp = self.client.post(
            self.list_url, {"title": "My note", "body": "hi"}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 201)

    def test_user_can_edit_own(self):
        _login(self.client, "user")
        note = create_note(self.user, title="User note")
        resp = self.client.patch(
            reverse("atlas-note-detail", kwargs={"note_id": note.pk}),
            {"title": "Updated"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_user_cannot_delete(self):
        _login(self.client, "user")
        note = create_note(self.user, title="User note")
        resp = self.client.delete(
            reverse("atlas-note-detail", kwargs={"note_id": note.pk})
        )
        self.assertIn(resp.status_code, [401, 403])

    def test_admin_can_delete(self):
        _login(self.client, "admin")
        note = create_note(self.admin, title="Note to delete")
        resp = self.client.delete(
            reverse("atlas-note-detail", kwargs={"note_id": note.pk})
        )
        self.assertEqual(resp.status_code, 204)


# ---------------------------------------------------------------------------
# Notes CRUD tests
# ---------------------------------------------------------------------------

class NoteCRUDTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        _login(self.client, "admin")
        self.list_url = reverse("atlas-note-list")

    def _detail_url(self, pk):
        return reverse("atlas-note-detail", kwargs={"note_id": pk})

    def test_create_and_list(self):
        resp = self.client.post(self.list_url, {"title": "Note 1"}, content_type="application/json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["title"], "Note 1")

        list_resp = self.client.get(self.list_url)
        self.assertEqual(len(list_resp.json()), 1)

    def test_blank_title_returns_400(self):
        resp = self.client.post(self.list_url, {"title": "  "}, content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_get_detail(self):
        note = create_note(self.admin, title="Detail note")
        resp = self.client.get(self._detail_url(note.pk))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["title"], "Detail note")

    def test_get_missing_returns_404(self):
        resp = self.client.get(self._detail_url(99999))
        self.assertEqual(resp.status_code, 404)

    def test_patch(self):
        note = create_note(self.admin, title="Old")
        resp = self.client.patch(self._detail_url(note.pk), {"title": "New"}, content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["title"], "New")

    def test_delete(self):
        note = create_note(self.admin, title="Gone")
        self.client.delete(self._detail_url(note.pk))
        resp = self.client.get(self._detail_url(note.pk))
        self.assertEqual(resp.status_code, 404)

    def test_search_by_title(self):
        create_note(self.admin, title="Grocery items", body="milk butter")
        create_note(self.admin, title="Meeting agenda", body="discuss roadmap")
        resp = self.client.get(self.list_url + "?search=Grocery")
        self.assertEqual(resp.status_code, 200)
        titles = [n["title"] for n in resp.json()]
        self.assertIn("Grocery items", titles)
        self.assertNotIn("Meeting agenda", titles)

    def test_search_by_body(self):
        create_note(self.admin, title="Shopping", body="buy milk and eggs")
        create_note(self.admin, title="Random", body="nothing relevant")
        resp = self.client.get(self.list_url + "?search=milk")
        titles = [n["title"] for n in resp.json()]
        self.assertIn("Shopping", titles)
        self.assertNotIn("Random", titles)

    def test_soft_deleted_not_in_list(self):
        note = create_note(self.admin, title="Hidden")
        note.soft_delete()
        resp = self.client.get(self.list_url)
        titles = [n["title"] for n in resp.json()]
        self.assertNotIn("Hidden", titles)


# ---------------------------------------------------------------------------
# Visibility mixin tests
# ---------------------------------------------------------------------------

class NoteVisibilityTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        self.user = _make_user("user", User.Role.USER)
        self.guest = _make_user("guest", User.Role.GUEST)
        self.child = _make_user("child", User.Role.USER, is_child=True)
        self.list_url = reverse("atlas-note-list")

    def test_household_note_visible_to_all_roles(self):
        create_note(self.admin, title="Household note", visibility="household")
        for username in ("user", "guest", "child"):
            with self.subTest(username=username):
                self.client.logout()
                _login(self.client, username)
                resp = self.client.get(self.list_url)
                titles = [n["title"] for n in resp.json()]
                self.assertIn("Household note", titles)

    def test_private_note_visible_only_to_creator(self):
        note = create_note(self.user, title="Private note", visibility="private")
        # user can see own private note
        _login(self.client, "user")
        resp = self.client.get(self.list_url)
        self.assertIn("Private note", [n["title"] for n in resp.json()])

        # guest cannot see it
        self.client.logout()
        _login(self.client, "guest")
        resp = self.client.get(self.list_url)
        self.assertNotIn("Private note", [n["title"] for n in resp.json()])

    def test_role_restricted_hidden_from_user(self):
        create_note(self.admin, title="Admin only", visibility="role_restricted")
        _login(self.client, "user")
        resp = self.client.get(self.list_url)
        self.assertNotIn("Admin only", [n["title"] for n in resp.json()])

    def test_role_restricted_visible_to_manager(self):
        create_note(self.admin, title="Manager note", visibility="role_restricted")
        manager = _make_user("manager", User.Role.MANAGER)
        _login(self.client, "manager")
        resp = self.client.get(self.list_url)
        self.assertIn("Manager note", [n["title"] for n in resp.json()])

    def test_child_cannot_see_sensitive(self):
        create_note(self.admin, title="Health info", sensitivity="sensitive")
        _login(self.client, "child")
        resp = self.client.get(self.list_url)
        self.assertNotIn("Health info", [n["title"] for n in resp.json()])


# ---------------------------------------------------------------------------
# Lists + Items tests
# ---------------------------------------------------------------------------

class AtlasListTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        _login(self.client, "admin")
        self.list_url = reverse("atlas-list-list")

    def _detail_url(self, pk):
        return reverse("atlas-list-detail", kwargs={"list_id": pk})

    def test_create_list(self):
        resp = self.client.post(
            self.list_url,
            {"title": "Shopping", "list_type": "grocery"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["title"], "Shopping")

    def test_list_endpoint_returns_id_and_items(self):
        # Regression: GET /atlas/lists/ must use the read serializer (id + nested items),
        # not the write serializer — the frontend renders list.items and would crash otherwise.
        atlas_list = create_atlas_list(self.admin, title="Chores", list_type="checklist")
        create_list_item(self.admin, atlas_list, title="Sweep")
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, 200)
        row = resp.json()[0]
        self.assertIn("id", row)
        self.assertIn("items", row)
        self.assertEqual(len(row["items"]), 1)
        self.assertEqual(row["items"][0]["title"], "Sweep")

    def test_add_item_and_list(self):
        atlas_list = create_atlas_list(self.admin, title="Chores", list_type="checklist")
        item_url = reverse("atlas-list-item-list", kwargs={"list_id": atlas_list.pk})
        resp = self.client.post(item_url, {"title": "Vacuum living room"}, content_type="application/json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["title"], "Vacuum living room")
        self.assertFalse(resp.json()["is_complete"])

    def test_complete_item(self):
        atlas_list = create_atlas_list(self.admin, title="Tasks", list_type="todo")
        item = create_list_item(self.admin, atlas_list, title="Call dentist")
        complete_url = reverse(
            "atlas-list-item-complete",
            kwargs={"list_id": atlas_list.pk, "item_id": item.pk},
        )
        resp = self.client.post(complete_url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["is_complete"])
        self.assertIsNotNone(resp.json()["completed_at"])

    def test_uncomplete_item(self):
        atlas_list = create_atlas_list(self.admin, title="Tasks", list_type="todo")
        item = create_list_item(self.admin, atlas_list, title="Buy milk")
        self.client.post(reverse(
            "atlas-list-item-complete",
            kwargs={"list_id": atlas_list.pk, "item_id": item.pk},
        ))
        resp = self.client.post(reverse(
            "atlas-list-item-uncomplete",
            kwargs={"list_id": atlas_list.pk, "item_id": item.pk},
        ))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["is_complete"])

    def test_delete_list(self):
        atlas_list = create_atlas_list(self.admin, title="Gone list", list_type="general")
        self.client.delete(self._detail_url(atlas_list.pk))
        resp = self.client.get(self._detail_url(atlas_list.pk))
        self.assertEqual(resp.status_code, 404)

    def test_item_from_wrong_list_returns_404(self):
        list1 = create_atlas_list(self.admin, title="L1", list_type="todo")
        list2 = create_atlas_list(self.admin, title="L2", list_type="todo")
        item = create_list_item(self.admin, list1, title="Item on L1")
        resp = self.client.patch(
            reverse("atlas-list-item-detail", kwargs={"list_id": list2.pk, "item_id": item.pk}),
            {"title": "x"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# Reminder calendar sync tests (D7)
# ---------------------------------------------------------------------------

class ReminderCalendarSyncTests(TestCase):
    """Verifies that creating/updating/deleting an AtlasReminder keeps its
    CalendarEvent in sync via the scheduling helper (D7)."""

    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)

    def test_dated_reminder_creates_calendar_event(self):
        reminder = create_reminder(self.admin, title="Doctor appointment", due_at=_future(48))
        self.assertIsNotNone(reminder.calendar_event_id)
        event = CalendarEvent.objects.get(pk=reminder.calendar_event_id)
        self.assertEqual(event.title, "Doctor appointment")
        self.assertEqual(event.source_record_type, "AtlasReminder")
        self.assertEqual(event.source_record_id, reminder.pk)

    def test_undated_reminder_has_no_event(self):
        reminder = create_reminder(self.admin, title="Undated reminder")
        self.assertIsNone(reminder.calendar_event_id)
        self.assertEqual(CalendarEvent.objects.filter(source_record_type="AtlasReminder").count(), 0)

    def test_adding_due_date_creates_event(self):
        reminder = create_reminder(self.admin, title="No date yet")
        self.assertIsNone(reminder.calendar_event_id)
        update_reminder(self.admin, reminder, due_at=_future(24))
        reminder.refresh_from_db()
        self.assertIsNotNone(reminder.calendar_event_id)

    def test_updating_title_syncs_to_event(self):
        reminder = create_reminder(self.admin, title="Old title", due_at=_future(24))
        update_reminder(self.admin, reminder, title="New title")
        event = CalendarEvent.objects.get(pk=reminder.calendar_event_id)
        self.assertEqual(event.title, "New title")

    def test_removing_due_date_deletes_event(self):
        reminder = create_reminder(self.admin, title="Was dated", due_at=_future(24))
        event_id = reminder.calendar_event_id
        self.assertIsNotNone(event_id)
        update_reminder(self.admin, reminder, due_at=None)
        reminder.refresh_from_db()
        self.assertIsNone(reminder.calendar_event_id)
        self.assertFalse(CalendarEvent.all_objects.filter(pk=event_id).exists())

    def test_deleting_reminder_deletes_event(self):
        reminder = create_reminder(self.admin, title="To delete", due_at=_future(24))
        event_id = reminder.calendar_event_id
        self.assertIsNotNone(event_id)
        delete_reminder(self.admin, reminder)
        self.assertFalse(CalendarEvent.all_objects.filter(pk=event_id).exists())

    def test_event_inherits_visibility_and_sensitivity(self):
        reminder = create_reminder(
            self.admin,
            title="Private reminder",
            due_at=_future(24),
            visibility="private",
            sensitivity="health",
        )
        event = CalendarEvent.objects.get(pk=reminder.calendar_event_id)
        self.assertEqual(event.visibility, "private")
        self.assertEqual(event.sensitivity, "health")

    def test_multiple_reminders_get_separate_events(self):
        r1 = create_reminder(self.admin, title="R1", due_at=_future(10))
        r2 = create_reminder(self.admin, title="R2", due_at=_future(20))
        self.assertNotEqual(r1.calendar_event_id, r2.calendar_event_id)
        self.assertEqual(CalendarEvent.objects.filter(source_record_type="AtlasReminder").count(), 2)

    def test_reminder_recipients_sync_to_calendar_event(self):
        person = Person.objects.create(
            household=get_active_household(), display_name="Alex", profile_type="adult",
        )
        reminder = create_reminder(
            self.admin,
            title="Call the school",
            due_at=_future(24),
            assigned_to_people=[person],
        )
        event = CalendarEvent.objects.get(pk=reminder.calendar_event_id)
        self.assertEqual(list(event.assigned_to_people.values_list("id", flat=True)), [person.id])


# ---------------------------------------------------------------------------
# Reminder API tests
# ---------------------------------------------------------------------------

class ReminderAPITests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        self.guest = _make_user("guest", User.Role.GUEST)
        _login(self.client, "admin")
        self.list_url = reverse("atlas-reminder-list")

    def _detail_url(self, pk):
        return reverse("atlas-reminder-detail", kwargs={"reminder_id": pk})

    def test_create_reminder(self):
        resp = self.client.post(
            self.list_url,
            {"title": "Pick up kids", "due_at": _future(2).isoformat()},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["title"], "Pick up kids")
        self.assertIsNotNone(resp.json()["calendar_event_id"])
        self.assertEqual(resp.json()["notification_state"], "scheduled")

    def test_create_reminder_with_notes_recipient_and_notifications(self):
        person = Person.objects.create(
            household=get_active_household(), display_name="Alex", profile_type="adult",
        )
        resp = self.client.post(
            self.list_url,
            {
                "title": "Medicine",
                "body": "Take with food",
                "due_at": _future(2).isoformat(),
                "assigned_to_person_ids": [person.id],
                "notifications_enabled": True,
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201, resp.json())
        self.assertEqual(resp.json()["body"], "Take with food")
        self.assertEqual(resp.json()["assigned_to_person_ids"], [person.id])

    def test_list_reminders(self):
        create_reminder(self.admin, title="R1")
        create_reminder(self.admin, title="R2")
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

    def test_get_detail(self):
        reminder = create_reminder(self.admin, title="Detail reminder")
        resp = self.client.get(self._detail_url(reminder.pk))
        self.assertEqual(resp.status_code, 200)

    def test_patch_reminder(self):
        reminder = create_reminder(self.admin, title="Old")
        resp = self.client.patch(
            self._detail_url(reminder.pk), {"title": "New"}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["title"], "New")

    def test_delete_reminder(self):
        reminder = create_reminder(self.admin, title="Bye")
        self.client.delete(self._detail_url(reminder.pk))
        resp = self.client.get(self._detail_url(reminder.pk))
        self.assertEqual(resp.status_code, 404)

    def test_guest_cannot_create(self):
        self.client.logout()
        _login(self.client, "guest")
        resp = self.client.post(
            self.list_url, {"title": "Guest reminder"}, content_type="application/json"
        )
        self.assertIn(resp.status_code, [401, 403])


# ---------------------------------------------------------------------------
# Unified search (B.1) + item fields (B.2)
# ---------------------------------------------------------------------------

class AtlasSearchTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        self.child = _make_user("child", User.Role.USER, is_child=True)
        self.url = reverse("atlas-search")

    def test_search_spans_notes_lists_items_reminders(self):
        create_note(self.admin, title="Camping note", body="tent and torch")
        lst = create_atlas_list(self.admin, title="Camping list", list_type="checklist")
        create_list_item(self.admin, lst, title="Pack the camping stove")
        create_reminder(self.admin, title="Book camping site", due_at=_future())
        _login(self.client, "admin")
        data = self.client.get(self.url + "?q=camping").json()
        self.assertTrue(data["notes"])
        self.assertTrue(data["lists"])
        self.assertTrue(data["items"])
        self.assertTrue(data["reminders"])

    def test_blank_query_returns_empty(self):
        _login(self.client, "admin")
        data = self.client.get(self.url + "?q=").json()
        self.assertEqual(data, {"notes": [], "lists": [], "items": [], "reminders": []})

    def test_search_hides_sensitive_note_from_child(self):
        create_note(self.admin, title="Secret stuff", body="private", sensitivity="sensitive")
        _login(self.client, "child")
        data = self.client.get(self.url + "?q=secret").json()
        self.assertEqual(data["notes"], [])

    def test_search_excludes_items_from_private_lists_for_other_users(self):
        # A private list owned by admin; its items must not surface for a child.
        private = create_atlas_list(self.admin, title="Hidden", visibility="private")
        create_list_item(self.admin, private, title="Secret widget")
        _login(self.client, "child")
        data = self.client.get(self.url + "?q=widget").json()
        self.assertEqual(data["items"], [])


class AtlasListItemFieldTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        _login(self.client, "admin")
        self.list = create_atlas_list(self.admin, title="Groceries", list_type="grocery")

    def test_create_item_with_quantity_and_due(self):
        url = reverse("atlas-list-item-list", kwargs={"list_id": self.list.pk})
        resp = self.client.post(
            url,
            {"title": "Milk", "quantity": "2 L", "due_at": _future().isoformat()},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body["quantity"], "2 L")
        self.assertIsNotNone(body["due_at"])
        self.assertEqual(body["atlas_list_id"], self.list.pk)

    def test_priority_defaults_blank_and_is_settable(self):
        item = create_list_item(self.admin, self.list, title="Vacuum cleaner")
        self.assertEqual(item.priority, "")
        url = reverse(
            "atlas-list-item-detail", kwargs={"list_id": self.list.pk, "item_id": item.pk}
        )
        resp = self.client.patch(url, {"priority": "high"}, content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.json())
        self.assertEqual(resp.json()["priority"], "high")
        item.refresh_from_db()
        self.assertEqual(item.priority, "high")

    def test_priority_rejects_unknown_value(self):
        url = reverse("atlas-list-item-list", kwargs={"list_id": self.list.pk})
        resp = self.client.post(
            url, {"title": "Vacuum cleaner", "priority": "urgent"}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


# ---------------------------------------------------------------------------
# Simplified Atlas product model (D19): Grocery, To-dos, notification offsets
# ---------------------------------------------------------------------------

class GroceryTests(TestCase):
    def setUp(self):
        self.admin = _make_user("groceryadmin", User.Role.ADMIN)
        _login(self.client, "groceryadmin")

    def test_household_has_exactly_one_grocery_list(self):
        first = self.client.get("/api/v1/atlas/grocery/").json()
        second = self.client.get("/api/v1/atlas/grocery/").json()
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(first["list_type"], "grocery")

    def test_item_creation_does_not_require_assignee(self):
        resp = self.client.post(
            "/api/v1/atlas/grocery/", {"title": "Apples"}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201, resp.json())
        self.assertEqual(resp.json()["assigned_to_person_ids"], [])

    def test_any_assignee_sent_is_ignored_for_grocery(self):
        person = Person.objects.create(
            household=get_active_household(), linked_user=self.admin, display_name="Nick",
            created_by=self.admin, updated_by=self.admin,
        )
        resp = self.client.post(
            "/api/v1/atlas/grocery/",
            {"title": "Bananas", "assigned_to_person_ids": [person.id]},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201, resp.json())
        self.assertEqual(resp.json()["assigned_to_person_ids"], [])

    def test_member_can_add_edit_and_check_items(self):
        grocery = self.client.get("/api/v1/atlas/grocery/").json()
        item_id = self.client.post(
            "/api/v1/atlas/grocery/", {"title": "Milk", "quantity": "2"}, content_type="application/json",
        ).json()["id"]
        edit_url = f"/api/v1/atlas/lists/{grocery['id']}/items/{item_id}/"
        resp = self.client.patch(edit_url, {"quantity": "3"}, content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["quantity"], "3")

        complete_url = f"/api/v1/atlas/lists/{grocery['id']}/items/{item_id}/complete/"
        resp = self.client.post(complete_url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["is_complete"])

        uncomplete_url = f"/api/v1/atlas/lists/{grocery['id']}/items/{item_id}/uncomplete/"
        resp = self.client.post(uncomplete_url)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["is_complete"])

    def test_bought_items_move_to_completed_and_clear_bought_removes_them(self):
        from apps.atlas.services import complete_list_item, ensure_household_grocery_list

        grocery = ensure_household_grocery_list(self.admin)
        bought = create_list_item(self.admin, grocery, title="Bread")
        complete_list_item(self.admin, bought)
        still_open = create_list_item(self.admin, grocery, title="Eggs")

        resp = self.client.get(f"/api/v1/atlas/lists/{grocery.id}/items/")
        titles_by_state = {row["title"]: row["is_complete"] for row in resp.json()}
        self.assertEqual(titles_by_state, {"Bread": True, "Eggs": False})

        clear_resp = self.client.post("/api/v1/atlas/grocery/clear-bought/")
        self.assertEqual(clear_resp.status_code, 200)
        self.assertEqual(clear_resp.json()["cleared"], 1)
        remaining_titles = [row["title"] for row in self.client.get(f"/api/v1/atlas/lists/{grocery.id}/items/").json()]
        self.assertEqual(remaining_titles, ["Eggs"])

    def test_duplicate_open_item_is_not_recreated(self):
        first = self.client.post(
            "/api/v1/atlas/grocery/", {"title": "Milk"}, content_type="application/json",
        ).json()
        second = self.client.post(
            "/api/v1/atlas/grocery/", {"title": "  milk "}, content_type="application/json",
        ).json()
        self.assertEqual(first["id"], second["id"])
        grocery = self.client.get("/api/v1/atlas/grocery/").json()
        self.assertEqual(len(grocery["items"]), 1)


class DashboardClassificationRegressionTests(TestCase):
    """apps.hub.tests covers the Hub widget end of D19 §K; this covers the selector directly."""

    def setUp(self):
        self.admin = _make_user("classifyadmin", User.Role.ADMIN)
        _login(self.client, "classifyadmin")

    def test_list_open_items_excludes_grocery_and_checklist(self):
        from apps.atlas import selectors

        todo_list = create_atlas_list(self.admin, title="Chores", list_type="todo")
        create_list_item(self.admin, todo_list, title="Mow the lawn")
        grocery_list = create_atlas_list(self.admin, title="Grocery", list_type="grocery")
        create_list_item(self.admin, grocery_list, title="Milk")
        checklist = create_atlas_list(self.admin, title="Packing", list_type="checklist")
        create_list_item(self.admin, checklist, title="Passport")

        titles = [item.title for item in selectors.list_open_items(self.admin)]
        self.assertEqual(titles, ["Mow the lawn"])

    def test_list_grocery_items_only_returns_grocery(self):
        from apps.atlas import selectors

        todo_list = create_atlas_list(self.admin, title="Chores", list_type="todo")
        create_list_item(self.admin, todo_list, title="Mow the lawn")
        grocery_list = create_atlas_list(self.admin, title="Grocery", list_type="grocery")
        create_list_item(self.admin, grocery_list, title="Milk")

        titles = [item.title for item in selectors.list_grocery_items(self.admin)]
        self.assertEqual(titles, ["Milk"])


class TodoListTests(TestCase):
    def setUp(self):
        self.admin_user = _make_user("todoadmin", User.Role.ADMIN)
        self.member_user = _make_user("todomember", User.Role.USER)
        self.admin_person = Person.objects.create(
            household=get_active_household(), linked_user=self.admin_user, display_name="Admin",
            created_by=self.admin_user, updated_by=self.admin_user,
        )
        self.member_person = Person.objects.create(
            household=get_active_household(), linked_user=self.member_user, display_name="Member",
            created_by=self.admin_user, updated_by=self.admin_user,
        )
        _login(self.client, "todoadmin")

    def test_household_and_personal_lists_are_created_on_first_use(self):
        lists = self.client.get("/api/v1/atlas/todos/lists/").json()
        titles = {row["title"]: row["owner_person_id"] for row in lists}
        self.assertIn("Household", titles)
        self.assertIsNone(titles["Household"])
        self.assertEqual(titles.get("Admin"), self.admin_person.id)
        self.assertEqual(titles.get("Member"), self.member_person.id)

    def test_quick_creation_requires_only_title(self):
        lists = {row["title"]: row["id"] for row in self.client.get("/api/v1/atlas/todos/lists/").json()}
        resp = self.client.post(
            f"/api/v1/atlas/lists/{lists['Household']}/items/",
            {"title": "Book pest inspection"}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201, resp.json())
        self.assertIsNone(resp.json()["due_at"])
        self.assertFalse(resp.json()["is_important"])
        self.assertEqual(resp.json()["notify_offsets"], [])

    def test_every_household_member_can_edit_household_and_others_personal_list(self):
        lists = {row["title"]: row["id"] for row in self.client.get("/api/v1/atlas/todos/lists/").json()}
        _login(self.client, "todomember")
        resp = self.client.post(
            f"/api/v1/atlas/lists/{lists['Admin']}/items/",
            {"title": "Pick up dry cleaning"}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201, resp.json())

    def test_moving_item_between_lists(self):
        lists = {row["title"]: row["id"] for row in self.client.get("/api/v1/atlas/todos/lists/").json()}
        item = self.client.post(
            f"/api/v1/atlas/lists/{lists['Household']}/items/",
            {"title": "Call plumber"}, content_type="application/json",
        ).json()
        resp = self.client.post(
            f"/api/v1/atlas/lists/{lists['Household']}/items/{item['id']}/move/",
            {"destination_list_id": lists["Admin"]}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200, resp.json())
        self.assertEqual(resp.json()["atlas_list_id"], lists["Admin"])

    def test_completion_leaves_active_list_and_is_restorable(self):
        lists = {row["title"]: row["id"] for row in self.client.get("/api/v1/atlas/todos/lists/").json()}
        item = self.client.post(
            f"/api/v1/atlas/lists/{lists['Household']}/items/",
            {"title": "Replace hallway globe"}, content_type="application/json",
        ).json()
        complete_resp = self.client.post(
            f"/api/v1/atlas/lists/{lists['Household']}/items/{item['id']}/complete/"
        )
        self.assertTrue(complete_resp.json()["is_complete"])
        restore_resp = self.client.post(
            f"/api/v1/atlas/lists/{lists['Household']}/items/{item['id']}/uncomplete/"
        )
        self.assertFalse(restore_resp.json()["is_complete"])

    def test_today_aggregates_overdue_and_due_today_across_lists(self):
        lists = {row["title"]: row["id"] for row in self.client.get("/api/v1/atlas/todos/lists/").json()}
        overdue_at = (timezone.now() - timezone.timedelta(days=2)).isoformat()
        today_at = timezone.now().isoformat()
        future_at = (timezone.now() + timezone.timedelta(days=5)).isoformat()
        self.client.post(
            f"/api/v1/atlas/lists/{lists['Household']}/items/",
            {"title": "Overdue household job", "due_at": overdue_at}, content_type="application/json",
        )
        self.client.post(
            f"/api/v1/atlas/lists/{lists['Admin']}/items/",
            {"title": "Due today personal job", "due_at": today_at}, content_type="application/json",
        )
        self.client.post(
            f"/api/v1/atlas/lists/{lists['Household']}/items/",
            {"title": "Future job", "due_at": future_at}, content_type="application/json",
        )
        self.client.post(
            f"/api/v1/atlas/lists/{lists['Household']}/items/",
            {"title": "No due date job"}, content_type="application/json",
        )
        titles = {row["title"] for row in self.client.get("/api/v1/atlas/todos/today/").json()}
        self.assertEqual(titles, {"Overdue household job", "Due today personal job"})


class TodoNotificationOffsetTests(TestCase):
    def setUp(self):
        self.admin = _make_user("notifyadmin", User.Role.ADMIN)
        _login(self.client, "notifyadmin")
        self.household_list = create_atlas_list(self.admin, title="Household", list_type="todo")

    def test_at_least_the_minimum_curated_offsets_are_accepted(self):
        resp = self.client.post(
            f"/api/v1/atlas/lists/{self.household_list.id}/items/",
            {"title": "Renew licence", "due_at": _future(48).isoformat(), "notify_offsets": [0, 60, 1440]},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201, resp.json())
        self.assertEqual(resp.json()["notify_offsets"], [0, 60, 1440])

    def test_unsupported_offset_is_rejected(self):
        resp = self.client.post(
            f"/api/v1/atlas/lists/{self.household_list.id}/items/",
            {"title": "Renew licence", "due_at": _future(48).isoformat(), "notify_offsets": [47]},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_offset_notification_fires_once_and_is_idempotent(self):
        from apps.notifications.models import Notification
        from apps.notifications.tasks import run_due_todo_offsets

        item = create_list_item(
            self.admin, self.household_list, title="Renew licence",
            due_at=timezone.now() + timezone.timedelta(minutes=30), notify_offsets=[60],
        )
        sent_first = run_due_todo_offsets()
        self.assertEqual(sent_first, 1)
        self.assertTrue(Notification.objects.filter(message="Renew licence").exists())
        sent_second = run_due_todo_offsets()
        self.assertEqual(sent_second, 0)
        self.assertEqual(Notification.objects.filter(message="Renew licence").count(), 1)

    def test_notification_reschedules_when_due_at_changes(self):
        from apps.atlas.services import update_list_item
        from apps.notifications.models import Notification
        from apps.notifications.tasks import run_due_todo_offsets

        item = create_list_item(
            self.admin, self.household_list, title="Renew licence",
            due_at=timezone.now() + timezone.timedelta(days=10), notify_offsets=[60],
        )
        self.assertEqual(run_due_todo_offsets(), 0)
        update_list_item(self.admin, item, due_at=timezone.now() + timezone.timedelta(minutes=30))
        self.assertEqual(run_due_todo_offsets(), 1)
        self.assertTrue(Notification.objects.filter(message="Renew licence").exists())

    def test_completing_item_prevents_future_notifications(self):
        from apps.atlas.services import complete_list_item
        from apps.notifications.tasks import run_due_todo_offsets

        item = create_list_item(
            self.admin, self.household_list, title="Renew licence",
            due_at=timezone.now() + timezone.timedelta(minutes=30), notify_offsets=[60],
        )
        complete_list_item(self.admin, item)
        self.assertEqual(run_due_todo_offsets(), 0)

    def test_deleting_item_prevents_future_notifications(self):
        from apps.atlas.services import delete_list_item
        from apps.notifications.tasks import run_due_todo_offsets

        item = create_list_item(
            self.admin, self.household_list, title="Renew licence",
            due_at=timezone.now() + timezone.timedelta(minutes=30), notify_offsets=[60],
        )
        delete_list_item(self.admin, item)
        self.assertEqual(run_due_todo_offsets(), 0)

    def test_clearing_offsets_stops_notifications(self):
        from apps.atlas.services import update_list_item
        from apps.notifications.tasks import run_due_todo_offsets

        item = create_list_item(
            self.admin, self.household_list, title="Renew licence",
            due_at=timezone.now() + timezone.timedelta(minutes=30), notify_offsets=[60],
        )
        update_list_item(self.admin, item, notify_offsets=[])
        self.assertEqual(run_due_todo_offsets(), 0)
