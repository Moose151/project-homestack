"""
accounts auth endpoint tests — Phase 1.3 (D6, API spec §2).

Tests cover PIN login, password login, logout, /me, and reauth.
Ordering mirrors the spec; permission-matrix tests come in Phase 1.5 (D10).
"""
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.accounts.services import REAUTH_SESSION_KEY
from apps.core.models import get_active_household


def _make_user(username="alice", display_name="Alice", role=User.Role.USER,
               pin="1234", password="alicepass!", is_child=False) -> User:
    user = User.objects.create_user(
        username=username,
        display_name=display_name,
        role=role,
        password=password,
        is_child_account=is_child,
    )
    user.set_pin(pin)
    user.save()
    return user


class PinLoginTests(TestCase):
    def setUp(self):
        self.user = _make_user()
        self.url = reverse("auth-pin-login")

    def test_valid_pin_returns_200_and_user_data(self):
        resp = self.client.post(self.url, {"username": "alice", "pin": "1234"}, content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["username"], "alice")

    def test_wrong_pin_returns_401(self):
        resp = self.client.post(self.url, {"username": "alice", "pin": "0000"}, content_type="application/json")
        self.assertEqual(resp.status_code, 401)

    def test_unknown_user_returns_401(self):
        resp = self.client.post(self.url, {"username": "nobody", "pin": "1234"}, content_type="application/json")
        self.assertEqual(resp.status_code, 401)

    def test_missing_fields_returns_400(self):
        resp = self.client.post(self.url, {"username": "alice"}, content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_inactive_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save()
        resp = self.client.post(self.url, {"username": "alice", "pin": "1234"}, content_type="application/json")
        self.assertEqual(resp.status_code, 401)

    def test_child_can_pin_login(self):
        child = _make_user(username="finn", display_name="Finn", is_child=True, pin="5678", password=None)
        child.set_unusable_password()
        child.save()
        resp = self.client.post(self.url, {"username": "finn", "pin": "5678"}, content_type="application/json")
        self.assertEqual(resp.status_code, 200)


class PasswordLoginTests(TestCase):
    def setUp(self):
        self.admin = _make_user(username="admin", display_name="Admin", role=User.Role.ADMIN,
                                 password="adminpass!")
        self.url = reverse("auth-password-login")

    def test_valid_password_returns_200(self):
        resp = self.client.post(self.url, {"username": "admin", "password": "adminpass!"}, content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["username"], "admin")

    def test_wrong_password_returns_401(self):
        resp = self.client.post(self.url, {"username": "admin", "password": "wrong"}, content_type="application/json")
        self.assertEqual(resp.status_code, 401)

    def test_child_cannot_password_login(self):
        child = _make_user(username="finn", display_name="Finn", is_child=True)
        child.set_unusable_password()
        child.save()
        resp = self.client.post(self.url, {"username": "finn", "password": "alicepass!"}, content_type="application/json")
        self.assertEqual(resp.status_code, 401)


class LogoutTests(TestCase):
    def setUp(self):
        self.user = _make_user()
        self.login_url = reverse("auth-pin-login")
        self.logout_url = reverse("auth-logout")

    def test_logout_ends_session(self):
        self.client.post(self.login_url, {"username": "alice", "pin": "1234"}, content_type="application/json")
        resp = self.client.post(self.logout_url)
        self.assertEqual(resp.status_code, 200)
        me_resp = self.client.get(reverse("auth-me"))
        self.assertEqual(me_resp.status_code, 401)


class MeTests(TestCase):
    def setUp(self):
        self.user = _make_user()
        self.login_url = reverse("auth-pin-login")
        self.me_url = reverse("auth-me")

    def test_unauthenticated_returns_401(self):
        resp = self.client.get(self.me_url)
        self.assertEqual(resp.status_code, 401)

    def test_authenticated_returns_user_data(self):
        self.client.post(self.login_url, {"username": "alice", "pin": "1234"}, content_type="application/json")
        resp = self.client.get(self.me_url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["username"], "alice")
        self.assertNotIn("password", data)
        self.assertNotIn("pin_hash", data)


class ReauthTests(TestCase):
    def setUp(self):
        self.user = _make_user(role=User.Role.ADMIN, password="alicepass!")
        self.login_url = reverse("auth-pin-login")
        self.reauth_url = reverse("auth-reauth")

    def _pin_login(self):
        self.client.post(self.login_url, {"username": "alice", "pin": "1234"}, content_type="application/json")

    def test_correct_password_sets_reauth_flag(self):
        self._pin_login()
        resp = self.client.post(self.reauth_url, {"password": "alicepass!"}, content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(self.client.session.get(REAUTH_SESSION_KEY))

    def test_wrong_password_returns_401(self):
        self._pin_login()
        resp = self.client.post(self.reauth_url, {"password": "wrong"}, content_type="application/json")
        self.assertEqual(resp.status_code, 401)

    def test_unauthenticated_reauth_returns_401(self):
        resp = self.client.post(self.reauth_url, {"password": "alicepass!"}, content_type="application/json")
        self.assertEqual(resp.status_code, 401)

    def test_child_cannot_reauth(self):
        child = _make_user(username="finn", display_name="Finn", is_child=True)
        child.set_unusable_password()
        child.save()
        self.client.post(self.login_url, {"username": "finn", "pin": "1234"}, content_type="application/json")
        resp = self.client.post(self.reauth_url, {"password": "alicepass!"}, content_type="application/json")
        self.assertEqual(resp.status_code, 401)
