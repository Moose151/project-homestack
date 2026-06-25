"""hub endpoint tests — Phase 1.9. Tests written first per D10.

Covers:
- GET /hub/ requires auth; returns widget list.
- GET /hub/kiosk/ requires auth; returns only kiosk-safe widgets.
- Hub content includes Atlas todos and reminders.
- GET /auth/kiosk-users/ returns persons with linked users (no auth required).
"""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.atlas.models import Visibility as AtlasVisibility
from apps.atlas.services import create_atlas_list, create_list_item, create_reminder
from apps.people.services import create_person
from apps.scheduling.models import CalendarEvent


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


class HubPermissionTests(TestCase):
    def test_unauthenticated_rejected(self):
        resp = self.client.get(reverse("hub"))
        self.assertIn(resp.status_code, [401, 403])

    def test_authenticated_gets_hub(self):
        _make_user("admin")
        _login(self.client, "admin")
        resp = self.client.get(reverse("hub"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("widgets", resp.json())

    def test_kiosk_hub_unauthenticated_rejected(self):
        resp = self.client.get(reverse("kiosk-hub"))
        self.assertIn(resp.status_code, [401, 403])

    def test_kiosk_hub_authenticated(self):
        _make_user("admin")
        _login(self.client, "admin")
        resp = self.client.get(reverse("kiosk-hub"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("widgets", resp.json())


class HubContentTests(TestCase):
    """Hub assembles Atlas widget content."""

    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        _login(self.client, "admin")

    def test_hub_contains_atlas_todos_widget(self):
        resp = self.client.get(reverse("hub"))
        widget_keys = [w["key"] for w in resp.json()["widgets"]]
        self.assertIn("atlas_todos", widget_keys)

    def test_hub_contains_atlas_reminders_widget(self):
        resp = self.client.get(reverse("hub"))
        widget_keys = [w["key"] for w in resp.json()["widgets"]]
        self.assertIn("atlas_reminders", widget_keys)

    def test_todos_widget_includes_open_items(self):
        atlas_list = create_atlas_list(self.admin, title="Chores", list_type="todo")
        create_list_item(self.admin, atlas_list, title="Clean bathroom")
        resp = self.client.get(reverse("hub"))
        todos = next(w for w in resp.json()["widgets"] if w["key"] == "atlas_todos")
        item_titles = [i["title"] for i in todos["items"]]
        self.assertIn("Clean bathroom", item_titles)

    def test_todos_widget_excludes_completed_items(self):
        from apps.atlas.services import complete_list_item
        atlas_list = create_atlas_list(self.admin, title="Tasks", list_type="todo")
        item = create_list_item(self.admin, atlas_list, title="Done task")
        complete_list_item(self.admin, item)
        resp = self.client.get(reverse("hub"))
        todos = next(w for w in resp.json()["widgets"] if w["key"] == "atlas_todos")
        item_titles = [i["title"] for i in todos["items"]]
        self.assertNotIn("Done task", item_titles)

    def test_reminders_widget_includes_upcoming(self):
        create_reminder(self.admin, title="Doctor visit", due_at=_future(48))
        resp = self.client.get(reverse("hub"))
        reminders_w = next(w for w in resp.json()["widgets"] if w["key"] == "atlas_reminders")
        titles = [r["title"] for r in reminders_w["items"]]
        self.assertIn("Doctor visit", titles)

    def test_reminders_widget_excludes_far_future(self):
        create_reminder(self.admin, title="Next year", due_at=_future(hours=24 * 30))
        resp = self.client.get(reverse("hub"))
        reminders_w = next(w for w in resp.json()["widgets"] if w["key"] == "atlas_reminders")
        titles = [r["title"] for r in reminders_w["items"]]
        self.assertNotIn("Next year", titles)

    def test_dated_reminder_appears_on_hub_and_calendar_once(self):
        reminder = create_reminder(self.admin, title="Book dentist", due_at=_future(36))
        self.assertIsNotNone(reminder.calendar_event_id)
        self.assertEqual(CalendarEvent.objects.filter(source_record_type="AtlasReminder", source_record_id=reminder.id).count(), 1)

        resp = self.client.get(reverse("hub"))
        reminders_w = next(w for w in resp.json()["widgets"] if w["key"] == "atlas_reminders")
        calendar_w = next(w for w in resp.json()["widgets"] if w["key"] == "calendar_upcoming")
        self.assertIn("Book dentist", [r["title"] for r in reminders_w["items"]])
        self.assertIn("Book dentist", [e["title"] for e in calendar_w["items"]])

    def test_todos_widget_hides_items_from_private_list_for_child(self):
        child = _make_user("child", User.Role.USER, is_child=True)
        private_list = create_atlas_list(
            self.admin, title="Private tasks", list_type="todo", visibility=AtlasVisibility.PRIVATE
        )
        create_list_item(self.admin, private_list, title="Hidden task")
        _login(self.client, "child")
        resp = self.client.get(reverse("hub"))
        todos = next(w for w in resp.json()["widgets"] if w["key"] == "atlas_todos")
        self.assertNotIn("Hidden task", [i["title"] for i in todos["items"]])

    def test_kiosk_hub_returns_kiosk_safe_widgets_only(self):
        resp = self.client.get(reverse("kiosk-hub"))
        for widget in resp.json()["widgets"]:
            self.assertTrue(widget["supports_kiosk"])


class KioskUsersTests(TestCase):
    """GET /auth/kiosk-users/ returns persons with linked users (no auth)."""

    def setUp(self):
        self.admin = _make_user("admin")
        self.url = reverse("kiosk-users")

    def test_no_auth_required(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_returns_persons_with_linked_users(self):
        person = create_person(self.admin, display_name="Alice Parent")
        person.linked_user = self.admin
        person.save()
        resp = self.client.get(self.url)
        names = [p["display_name"] for p in resp.json()]
        self.assertIn("Alice Parent", names)

    def test_person_without_linked_user_excluded(self):
        create_person(self.admin, display_name="Unlinked Child")
        resp = self.client.get(self.url)
        names = [p["display_name"] for p in resp.json()]
        self.assertNotIn("Unlinked Child", names)

    def test_response_includes_username(self):
        person = create_person(self.admin, display_name="Admin Person")
        person.linked_user = self.admin
        person.save()
        resp = self.client.get(self.url)
        entries = {p["display_name"]: p for p in resp.json()}
        self.assertIn("Admin Person", entries)
        self.assertEqual(entries["Admin Person"]["username"], "admin")


class HubWidgetConfigTests(TestCase):
    """M2.5 A.1 — widget configuration endpoints."""

    def setUp(self):
        self.admin = _make_user("admin", role=User.Role.ADMIN)
        self.user = _make_user("parentuser", role=User.Role.USER)

    def _config(self):
        return {w["key"]: w for w in self.client.get(reverse("hub-widget-config")).json()["widgets"]}

    def test_config_lists_catalogue_with_state(self):
        _login(self.client, "admin")
        cfg = self._config()
        self.assertIn("atlas_todos", cfg)
        self.assertIn("household_enabled", cfg["atlas_todos"])
        self.assertIn("user_hidden", cfg["atlas_todos"])

    def test_admin_can_configure_household_widget(self):
        _login(self.client, "admin")
        resp = self.client.patch(
            reverse("hub-widget-household", args=["atlas_todos"]),
            {"size": "large", "is_enabled": True},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._config()["atlas_todos"]["size"], "large")

    def test_non_admin_cannot_configure_household_widget(self):
        _login(self.client, "parentuser")
        resp = self.client.patch(
            reverse("hub-widget-household", args=["atlas_todos"]),
            {"size": "large"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_user_can_hide_own_widget(self):
        _login(self.client, "parentuser")
        resp = self.client.patch(
            reverse("hub-widget-user", args=["atlas_todos"]),
            {"is_enabled": False},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        keys = [w["key"] for w in self.client.get(reverse("hub")).json()["widgets"]]
        self.assertNotIn("atlas_todos", keys)

    def test_unknown_widget_key_rejected(self):
        _login(self.client, "admin")
        resp = self.client.patch(
            reverse("hub-widget-household", args=["nope_widget"]),
            {"size": "small"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
