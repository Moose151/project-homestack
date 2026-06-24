"""
Nodes endpoint tests — Phase 1.6, written FIRST per D10.

Permission matrix:
                           GET /nodes/  enable/disable/settings
unauthenticated                deny           deny
admin                          200            200
manager                        200            403
user                           200            403
guest                          200            403
child                          200            403
"""
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User


def _make_user(username, role=User.Role.USER, is_child=False, pin="1234") -> User:
    user = User.objects.create_user(
        username=username, display_name=username.title(),
        password="pass!", role=role, is_child_account=is_child,
    )
    user.set_pin(pin)
    user.save()
    return user


def _login(client, username, pin="1234"):
    client.post(reverse("auth-pin-login"), {"username": username, "pin": pin},
                content_type="application/json")


class NodeListViewTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", role=User.Role.ADMIN)
        self.manager = _make_user("manager", role=User.Role.MANAGER)
        self.user = _make_user("user")
        self.guest = _make_user("guest", role=User.Role.GUEST)
        self.child = _make_user("child", is_child=True)
        self.url = reverse("nodes-list")

    def test_unauthenticated_denied(self):
        resp = self.client.get(self.url)
        self.assertIn(resp.status_code, [401, 403])

    def test_admin_can_list(self):
        _login(self.client, "admin")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_manager_can_list(self):
        _login(self.client, "manager")
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_user_can_list(self):
        _login(self.client, "user")
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_guest_can_list(self):
        _login(self.client, "guest")
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_child_can_list(self):
        _login(self.client, "child")
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_list_contains_atlas(self):
        _login(self.client, "admin")
        resp = self.client.get(self.url)
        keys = [n["key"] for n in resp.json()]
        self.assertIn("atlas", keys)

    def test_atlas_is_enabled(self):
        _login(self.client, "admin")
        resp = self.client.get(self.url)
        atlas = next(n for n in resp.json() if n["key"] == "atlas")
        self.assertTrue(atlas["is_enabled"])

    def test_other_nodes_disabled(self):
        _login(self.client, "admin")
        resp = self.client.get(self.url)
        for node in resp.json():
            if node["key"] != "atlas":
                self.assertFalse(node["is_enabled"], f"{node['key']} should be disabled")


class NodeEnableDisableTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin2", role=User.Role.ADMIN)
        self.manager = _make_user("manager2", role=User.Role.MANAGER)
        self.user = _make_user("user2")

    def test_admin_can_enable_node(self):
        _login(self.client, "admin2")
        resp = self.client.post(reverse("nodes-enable", kwargs={"node_key": "pets"}))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["is_enabled"])

    def test_admin_can_disable_node(self):
        _login(self.client, "admin2")
        self.client.post(reverse("nodes-enable", kwargs={"node_key": "pets"}))
        resp = self.client.post(reverse("nodes-disable", kwargs={"node_key": "pets"}))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["is_enabled"])

    def test_manager_cannot_enable(self):
        _login(self.client, "manager2")
        resp = self.client.post(reverse("nodes-enable", kwargs={"node_key": "pets"}))
        self.assertEqual(resp.status_code, 403)

    def test_user_cannot_enable(self):
        _login(self.client, "user2")
        resp = self.client.post(reverse("nodes-enable", kwargs={"node_key": "pets"}))
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_cannot_enable(self):
        resp = self.client.post(reverse("nodes-enable", kwargs={"node_key": "pets"}))
        self.assertIn(resp.status_code, [401, 403])

    def test_unknown_node_returns_404(self):
        _login(self.client, "admin2")
        resp = self.client.post(reverse("nodes-enable", kwargs={"node_key": "nonexistent"}))
        self.assertEqual(resp.status_code, 404)


class NodeSettingsViewTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin3", role=User.Role.ADMIN)
        self.user = _make_user("user3")

    def test_admin_can_patch_settings(self):
        _login(self.client, "admin3")
        resp = self.client.patch(
            reverse("nodes-settings", kwargs={"node_key": "atlas"}),
            {"default_list_view": "grid"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        settings = {s["key"]: s["value"] for s in resp.json()}
        self.assertEqual(settings["default_list_view"], "grid")

    def test_user_cannot_patch_settings(self):
        _login(self.client, "user3")
        resp = self.client.patch(
            reverse("nodes-settings", kwargs={"node_key": "atlas"}),
            {"key": "foo", "value": "bar"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_unknown_node_settings_returns_404(self):
        _login(self.client, "admin3")
        resp = self.client.patch(
            reverse("nodes-settings", kwargs={"node_key": "nonexistent"}),
            {"key": "foo", "value": "bar"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 404)
