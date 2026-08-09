"""Elevation expires sooner on the kiosk than on the web (Milestone 4, D6 §6).

The kiosk is a shared always-on screen in a communal room. A five-minute elevated session is a
reasonable convenience on a personal laptop and an open door on a screen anybody walks past, so
the kiosk gets a much shorter window. Permission tests first (D10).
"""
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.services import REAUTH_SESSION_KEY
from apps.nodes.services import enable_node


def _adult() -> User:
    user = User.objects.create_user(
        username="adult", display_name="Adult", role=User.Role.ADMIN, password="pass123!"
    )
    user.set_pin("1234")
    user.save()
    return user


class KioskReauthWindowTests(TestCase):
    def setUp(self):
        self.user = _adult()
        # Solace is gated on every request, including reads, so it actually exercises the window.
        enable_node(self.user, "solace")
        self.gated_url = reverse("solace-bill-list")

    def _login(self, surface: str | None = None):
        payload = {"username": "adult", "pin": "1234"}
        if surface is not None:
            payload["surface"] = surface
        return self.client.post(
            reverse("auth-pin-login"), payload, content_type="application/json"
        )

    def _reauth(self):
        return self.client.post(
            reverse("auth-reauth"), {"password": "pass123!"}, content_type="application/json"
        )

    def _age_elevation(self, seconds: int):
        session = self.client.session
        session[REAUTH_SESSION_KEY] = int(timezone.now().timestamp()) - seconds
        session.save()

    def test_web_session_keeps_the_longer_window(self):
        """The web has to say so. Silence is treated as the shared screen, not the private one."""
        self._login(surface="web")
        self._reauth()
        self._age_elevation(120)
        self.assertEqual(self.client.get(self.gated_url).status_code, 200)

    @override_settings(KIOSK_REAUTH_TTL_SECONDS=60)
    def test_kiosk_session_expires_sooner(self):
        self._login(surface="kiosk")
        self._reauth()
        self._age_elevation(120)
        self.assertEqual(
            self.client.get(self.gated_url).status_code, 403,
            "two minutes is inside the web window but past the kiosk one",
        )

    @override_settings(KIOSK_REAUTH_TTL_SECONDS=60)
    def test_kiosk_session_still_works_inside_its_window(self):
        self._login(surface="kiosk")
        self._reauth()
        self._age_elevation(10)
        self.assertEqual(self.client.get(self.gated_url).status_code, 200)

    @override_settings(KIOSK_REAUTH_TTL_SECONDS=60)
    def test_a_client_that_does_not_say_gets_the_short_window(self):
        """A future client that forgets to declare itself must not be handed the long window."""
        self._login()
        self._reauth()
        self._age_elevation(120)
        self.assertEqual(self.client.get(self.gated_url).status_code, 403)

    @override_settings(KIOSK_REAUTH_TTL_SECONDS=60)
    def test_an_unrecognised_surface_is_treated_as_the_kiosk(self):
        self._login(surface="something-else")
        self._reauth()
        self._age_elevation(120)
        self.assertEqual(self.client.get(self.gated_url).status_code, 403)

    def test_logging_in_again_on_the_web_clears_the_kiosk_marking(self):
        self._login(surface="kiosk")
        self.client.post(reverse("auth-logout"))
        self._login(surface="web")
        self._reauth()
        self._age_elevation(120)
        self.assertEqual(self.client.get(self.gated_url).status_code, 200)
