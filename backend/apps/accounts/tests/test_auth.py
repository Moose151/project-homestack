"""
accounts auth endpoint tests — Phase 1.3 (D6, API spec §2).

Tests cover PIN login, password login, logout, /me, and reauth.
Ordering mirrors the spec; permission-matrix tests come in Phase 1.5 (D10).
"""
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.services import REAUTH_SESSION_KEY, is_reauthed
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

    def test_password_change_preserves_session(self):
        self.client.post(self.login_url, {"username": "alice", "pin": "1234"}, content_type="application/json")
        resp = self.client.patch(
            self.me_url,
            {"password": "new-alice-password!"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.get(self.me_url).status_code, 200)
        self.assertEqual(
            self.client.post(
                reverse("auth-reauth"),
                {"password": "new-alice-password!"},
                content_type="application/json",
            ).status_code,
            200,
        )


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

    def test_guest_cannot_reauth(self):
        guest = _make_user(
            username="visitor",
            display_name="Visitor",
            role=User.Role.GUEST,
            password="guestpass!",
        )
        self.client.force_login(guest)
        resp = self.client.post(
            self.reauth_url,
            {"password": "guestpass!"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)

    @override_settings(REAUTH_TTL_SECONDS=60)
    def test_reauth_state_expires_and_is_removed(self):
        request = RequestFactory().get("/")
        SessionMiddleware(lambda _request: None).process_request(request)
        request.session[REAUTH_SESSION_KEY] = int(timezone.now().timestamp()) - 61

        self.assertFalse(is_reauthed(request))
        self.assertNotIn(REAUTH_SESSION_KEY, request.session)

    def test_legacy_boolean_reauth_state_is_not_trusted(self):
        request = RequestFactory().get("/")
        SessionMiddleware(lambda _request: None).process_request(request)
        request.session[REAUTH_SESSION_KEY] = True

        self.assertFalse(is_reauthed(request))


class GuideDismissalTests(TestCase):
    def setUp(self):
        self.user = _make_user()
        self.other = _make_user(username="bob", display_name="Bob")
        self.url = reverse("guide-dismissals")

    def test_dismissal_survives_a_new_login_session(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.url,
            {"guide_identifier": "homestead", "guide_version": "1"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.client.logout()
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).json(), [
            {"guide_identifier": "homestead", "guide_version": "1"},
        ])

    def test_dismissals_are_per_user_and_per_guide_version(self):
        self.client.force_login(self.user)
        for version in ("1", "2"):
            self.client.post(
                self.url,
                {"guide_identifier": "atlas", "guide_version": version},
                content_type="application/json",
            )
        self.assertEqual(len(self.client.get(self.url).json()), 2)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).json(), [])

    def test_reset_removes_only_the_current_users_dismissals(self):
        for user in (self.user, self.other):
            self.client.force_login(user)
            self.client.post(
                self.url,
                {"guide_identifier": "hub", "guide_version": "1"},
                content_type="application/json",
            )
        self.client.force_login(self.user)
        self.assertEqual(self.client.delete(self.url).status_code, 200)
        self.assertEqual(self.client.get(self.url).json(), [])
        self.client.force_login(self.other)
        self.assertEqual(len(self.client.get(self.url).json()), 1)


class UserPreferenceTests(TestCase):
    """The generic per-user UI preference store (tab order, mobile dock shortcuts).

    The store is deliberately bounded: only registered keys exist, and each value is validated
    into a normal form. It carries no authority — permission filtering happens where a
    preference is *applied*, never here.
    """

    def setUp(self):
        self.user = _make_user()
        self.other = _make_user(username="bob", display_name="Bob")
        self.url = reverse("user-preferences")

    def _patch(self, payload):
        return self.client.patch(self.url, payload, content_type="application/json")

    def test_defaults_are_returned_when_nothing_is_saved(self):
        self.client.force_login(self.user)
        self.assertEqual(
            self.client.get(self.url).json(),
            {"tab_order": {}, "mobile_nav": [], "sidebar_collapsed": False},
        )

    def test_tab_order_persists_across_sessions(self):
        self.client.force_login(self.user)
        self._patch({"tab_order": {"solace": ["bills", "now", "purchases", "plan"]}})
        self.client.logout()
        self.client.force_login(self.user)
        self.assertEqual(
            self.client.get(self.url).json()["tab_order"]["solace"],
            ["bills", "now", "purchases", "plan"],
        )

    def test_preferences_are_isolated_per_user(self):
        self.client.force_login(self.user)
        self._patch({"tab_order": {"solace": ["bills", "now"]}})
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).json()["tab_order"], {})

    def test_patching_one_page_does_not_wipe_another(self):
        self.client.force_login(self.user)
        self._patch({"tab_order": {"solace": ["bills", "now"]}})
        self._patch({"tab_order": {"homestead": ["rooms", "overview"]}})
        saved = self.client.get(self.url).json()["tab_order"]
        self.assertEqual(saved["solace"], ["bills", "now"])
        self.assertEqual(saved["homestead"], ["rooms", "overview"])

    def test_empty_page_order_resets_just_that_page(self):
        self.client.force_login(self.user)
        self._patch({"tab_order": {"solace": ["bills", "now"], "homestead": ["rooms"]}})
        self._patch({"tab_order": {"solace": []}})
        saved = self.client.get(self.url).json()["tab_order"]
        self.assertNotIn("solace", saved)
        self.assertEqual(saved["homestead"], ["rooms"])

    def test_delete_resets_everything_for_this_user_only(self):
        for user in (self.user, self.other):
            self.client.force_login(user)
            self._patch({"mobile_nav": ["solace", "atlas"]})
        self.client.force_login(self.user)
        self.assertEqual(self.client.delete(self.url).status_code, 200)
        self.assertEqual(self.client.get(self.url).json()["mobile_nav"], [])
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).json()["mobile_nav"], ["solace", "atlas"])

    def test_delete_can_reset_a_single_key(self):
        self.client.force_login(self.user)
        self._patch({"mobile_nav": ["solace"], "tab_order": {"solace": ["bills"]}})
        self.client.delete(f"{self.url}?key=mobile_nav")
        saved = self.client.get(self.url).json()
        self.assertEqual(saved["mobile_nav"], [])
        self.assertEqual(saved["tab_order"], {"solace": ["bills"]})

    # --- the bounds that keep this from being an open JSON dump ---

    def test_unknown_preference_key_is_rejected(self):
        self.client.force_login(self.user)
        self.assertEqual(self._patch({"is_admin": True}).status_code, 400)

    def test_unknown_key_cannot_be_smuggled_in_alongside_a_valid_one(self):
        self.client.force_login(self.user)
        response = self._patch({"tab_order": {"solace": ["bills"]}, "superuser": True})
        self.assertEqual(response.status_code, 400)
        # ...and the valid half must not have been written either.
        self.assertEqual(self.client.get(self.url).json()["tab_order"], {})

    def test_malformed_tab_order_shapes_are_rejected(self):
        self.client.force_login(self.user)
        for payload in (
            {"tab_order": ["bills"]},
            {"tab_order": {"solace": "bills"}},
            {"tab_order": {"solace": [{"key": "bills"}]}},
            {"tab_order": {"BAD KEY": ["bills"]}},
            {"tab_order": {"solace": ["../../etc/passwd"]}},
        ):
            self.assertEqual(self._patch(payload).status_code, 400, payload)

    def test_oversized_values_are_rejected(self):
        self.client.force_login(self.user)
        self.assertEqual(
            self._patch({"tab_order": {"solace": [f"tab{n}" for n in range(80)]}}).status_code,
            400,
        )
        self.assertEqual(
            self._patch({"tab_order": {f"page{n}": ["a"] for n in range(60)}}).status_code,
            400,
        )

    def test_mobile_nav_is_capped_at_two_slots(self):
        self.client.force_login(self.user)
        self.assertEqual(
            self._patch({"mobile_nav": ["solace", "atlas", "pets"]}).status_code, 400,
        )

    def test_duplicate_mobile_nav_entries_are_collapsed(self):
        self.client.force_login(self.user)
        self._patch({"mobile_nav": ["solace", "solace"]})
        self.assertEqual(self.client.get(self.url).json()["mobile_nav"], ["solace"])

    def test_sidebar_collapse_persists_per_user(self):
        """Desktop sidebar state lives here so it follows the person, not the browser."""
        self.client.force_login(self.user)
        self._patch({"sidebar_collapsed": True})
        self.client.logout()
        self.client.force_login(self.user)
        self.assertTrue(self.client.get(self.url).json()["sidebar_collapsed"])

    def test_sidebar_collapse_is_isolated_between_users(self):
        self.client.force_login(self.user)
        self._patch({"sidebar_collapsed": True})
        self.client.force_login(self.other)
        self.assertFalse(self.client.get(self.url).json()["sidebar_collapsed"])

    def test_sidebar_collapse_can_be_switched_back_off(self):
        self.client.force_login(self.user)
        self._patch({"sidebar_collapsed": True})
        self._patch({"sidebar_collapsed": False})
        self.assertFalse(self.client.get(self.url).json()["sidebar_collapsed"])

    def test_a_non_boolean_sidebar_value_falls_back_to_expanded(self):
        """A presentation flag must never become a way to store arbitrary content."""
        self.client.force_login(self.user)
        self._patch({"sidebar_collapsed": "yes please"})
        self.assertFalse(self.client.get(self.url).json()["sidebar_collapsed"])

    def test_preferences_require_authentication(self):
        self.assertEqual(self.client.get(self.url).status_code, 403)
