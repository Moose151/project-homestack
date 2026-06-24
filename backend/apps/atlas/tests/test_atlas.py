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
from apps.atlas.services import (
    create_atlas_list,
    create_list_item,
    create_note,
    create_reminder,
    delete_reminder,
    update_reminder,
)
from apps.scheduling.models import CalendarEvent


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
