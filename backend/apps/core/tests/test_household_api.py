"""
Household endpoint tests — Phase 1.6, written FIRST per D10.

GET /api/v1/household/ — everyone with household.view
PATCH /api/v1/household/ — admin only (household.edit)
"""
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User


def _make_user(username, role=User.Role.USER, pin="1234") -> User:
    user = User.objects.create_user(
        username=username, display_name=username.title(),
        password="pass!", role=role,
    )
    user.set_pin(pin)
    user.save()
    return user


def _login(client, username, pin="1234"):
    client.post(reverse("auth-pin-login"), {"username": username, "pin": pin},
                content_type="application/json")


class HouseholdGetTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", role=User.Role.ADMIN)
        self.user = _make_user("user")
        self.url = reverse("household")

    def test_unauthenticated_denied(self):
        resp = self.client.get(self.url)
        self.assertIn(resp.status_code, [401, 403])

    def test_admin_can_get(self):
        _login(self.client, "admin")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("name", data)
        self.assertIn("timezone", data)
        self.assertIn("slug", data)

    def test_user_can_get(self):
        _login(self.client, "user")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)


class HouseholdPatchTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin2", role=User.Role.ADMIN)
        self.manager = _make_user("manager2", role=User.Role.MANAGER)
        self.user = _make_user("user2")
        self.url = reverse("household")

    def test_unauthenticated_cannot_patch(self):
        resp = self.client.patch(self.url, {"name": "X"}, content_type="application/json")
        self.assertIn(resp.status_code, [401, 403])

    def test_admin_can_patch_name(self):
        _login(self.client, "admin2")
        resp = self.client.patch(self.url, {"name": "Updated Name"},
                                 content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["name"], "Updated Name")

    def test_admin_can_patch_timezone(self):
        _login(self.client, "admin2")
        resp = self.client.patch(self.url, {"timezone": "Europe/London"},
                                 content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["timezone"], "Europe/London")

    def test_admin_can_set_calendar_defaults(self):
        _login(self.client, "admin2")
        resp = self.client.patch(
            self.url,
            {"calendar_default_view": "week", "calendar_week_start": 0, "calendar_time_format": "24h"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["calendar_default_view"], "week")
        self.assertEqual(data["calendar_week_start"], 0)
        self.assertEqual(data["calendar_time_format"], "24h")

    def test_calendar_defaults_exposed_on_get(self):
        _login(self.client, "admin2")
        data = self.client.get(self.url).json()
        self.assertIn("calendar_default_view", data)
        self.assertIn("calendar_week_start", data)
        self.assertIn("calendar_time_format", data)

    def test_manager_cannot_patch(self):
        _login(self.client, "manager2")
        resp = self.client.patch(self.url, {"name": "Hack"}, content_type="application/json")
        self.assertEqual(resp.status_code, 403)

    def test_user_cannot_patch(self):
        _login(self.client, "user2")
        resp = self.client.patch(self.url, {"name": "Hack"}, content_type="application/json")
        self.assertEqual(resp.status_code, 403)
