"""CSRF regression tests (Milestone 1 fix).

DRF's SessionAuthentication enforces CSRF on authenticated unsafe requests. The SPA
obtains a token from the csrftoken cookie (seeded by /auth/me/ and /auth/kiosk-users/)
and returns it via the X-CSRFToken header. These tests use a CSRF-enforcing client —
like a real browser — because the default test client bypasses CSRF entirely.
"""
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import User


def _make_admin() -> User:
    user = User.objects.create_user(
        username="csrfadmin", display_name="Admin", role=User.Role.ADMIN, password="pass123!"
    )
    user.set_pin("1234")
    user.save()
    return user


class CsrfFlowTests(TestCase):
    def setUp(self):
        _make_admin()
        self.client = Client(enforce_csrf_checks=True)

    def _bootstrap_and_login(self) -> str:
        # /auth/me/ seeds the csrftoken cookie even when unauthenticated.
        self.client.get(reverse("auth-me"))
        self.assertIn("csrftoken", self.client.cookies)
        resp = self.client.post(
            reverse("auth-pin-login"),
            {"username": "csrfadmin", "pin": "1234"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        return self.client.cookies["csrftoken"].value

    def test_login_works_without_csrf_token(self):
        # Login endpoints are CSRF-exempt (no session yet); they must work tokenless.
        self.client.get(reverse("auth-me"))
        resp = self.client.post(
            reverse("auth-pin-login"),
            {"username": "csrfadmin", "pin": "1234"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_authenticated_write_succeeds_with_token(self):
        token = self._bootstrap_and_login()
        resp = self.client.post(
            reverse("atlas-note-list"),
            {"title": "Hello"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(resp.status_code, 201)

    def test_authenticated_write_rejected_without_token(self):
        self._bootstrap_and_login()
        resp = self.client.post(
            reverse("atlas-note-list"),
            {"title": "Hello"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_me_sets_csrf_cookie(self):
        resp = self.client.get(reverse("auth-me"))
        # Unauthenticated returns 401 but the cookie is still seeded for the next write.
        self.assertEqual(resp.status_code, 401)
        self.assertIn("csrftoken", self.client.cookies)
