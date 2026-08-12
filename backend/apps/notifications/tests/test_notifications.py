"""Notifications tests (Milestone 2, Phase 2.15)."""
from datetime import time
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.meridian import services as meridian
from apps.nodes.models import HouseholdNode
from apps.notifications import selectors, services
from apps.notifications.models import Notification, PushDevice, UserNotificationSettings
from apps.people.models import Person


def _make_user(username, role=User.Role.ADMIN, is_child=False):
    user = User.objects.create_user(
        username=username, display_name=username.capitalize(), role=role, password="pass123!"
    )
    user.set_pin("1234")
    user.is_child_account = is_child
    user.save()
    return user


def _make_person(name, *, linked_user=None):
    from apps.core.models import get_active_household
    return Person.objects.create(
        household=get_active_household(), display_name=name,
        profile_type=Person.ProfileType.CHILD, linked_user=linked_user,
    )


class NotificationServiceTests(TestCase):
    def setUp(self):
        self.user = _make_user("parent")

    def test_create_and_unread_count(self):
        services.create_notification(self.user, title="Hi", message="There")
        self.assertEqual(selectors.unread_count(self.user), 1)

    def test_notify_person_with_login(self):
        child_user = _make_user("kid", role=User.Role.USER, is_child=True)
        person = _make_person("Finn", linked_user=child_user)
        services.notify_person(person, title="T", message="M")
        self.assertEqual(selectors.unread_count(child_user), 1)

    def test_notify_person_without_login_is_noop(self):
        person = _make_person("NoLogin")
        result = services.notify_person(person, title="T", message="M")
        self.assertIsNone(result)
        self.assertEqual(Notification.objects.count(), 0)

    def test_mark_all_read(self):
        services.create_notification(self.user, title="a", message="m")
        services.create_notification(self.user, title="b", message="m")
        services.mark_all_read(self.user)
        self.assertEqual(selectors.unread_count(self.user), 0)


class NotificationWiringTests(TestCase):
    """Meridian/achievements actions surface as notifications to the right user."""

    def setUp(self):
        self.admin = _make_user("admin")
        self.child_user = _make_user("kid", role=User.Role.USER, is_child=True)
        self.person = _make_person("Finn", linked_user=self.child_user)

    def test_task_approval_notifies_child(self):
        task = meridian.create_task(self.admin, title="Tidy", points=5,
                                    assigned_to_people=[self.person])
        meridian.complete_task(self.admin, task, person_id=self.person.id)
        meridian.approve_task(self.admin, task)
        notes = selectors.list_for_user(self.child_user)
        self.assertTrue(any("approved" in n.title.lower() for n in notes))

    def test_badge_earned_notifies_child(self):
        # First approved task earns the "first_task" badge → a badge notification too.
        task = meridian.create_task(self.admin, title="Tidy", points=5,
                                    assigned_to_people=[self.person])
        meridian.complete_task(self.admin, task, person_id=self.person.id)
        meridian.approve_task(self.admin, task)
        self.assertTrue(
            Notification.objects.filter(recipient_user=self.child_user, title="Badge earned!").exists()
        )


class NotificationApiTests(TestCase):
    def setUp(self):
        self.user = _make_user("parent")

    def _login(self):
        self.client.post(
            reverse("auth-pin-login"),
            {"username": "parent", "pin": "1234"}, content_type="application/json",
        )

    def test_list_and_mark_read(self):
        note = services.create_notification(self.user, title="Hi", message="m")
        self._login()
        resp = self.client.get(reverse("notification-list"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["unread_count"], 1)
        resp = self.client.post(reverse("notification-read", args=[note.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(selectors.unread_count(self.user), 0)

    def test_only_see_own_notifications(self):
        other = _make_user("other", role=User.Role.USER)
        services.create_notification(other, title="theirs", message="m")
        self._login()
        resp = self.client.get(reverse("notification-list"))
        self.assertEqual(len(resp.json()["results"]), 0)


class NotificationPreferenceGateTests(TestCase):
    """docs/32_Core_Notifications_and_Push.md §5 — the central preference gate."""

    def setUp(self):
        self.user = _make_user("parent")

    def test_blank_category_always_creates_matching_pre_existing_behaviour(self):
        note = services.create_notification(self.user, title="T", message="M")
        self.assertIsNotNone(note)

    def test_missing_preference_row_defaults_to_enabled(self):
        note = services.create_notification(self.user, title="T", message="M", category="meridian")
        self.assertIsNotNone(note)

    def test_disabled_category_suppresses_the_notification(self):
        services.set_preference(
            self.user, category="meridian", in_app_enabled=False, push_enabled=True,
        )
        note = services.create_notification(self.user, title="T", message="M", category="meridian")
        self.assertIsNone(note)
        self.assertEqual(Notification.objects.count(), 0)

    def test_enabling_a_previously_disabled_category_restores_delivery(self):
        services.set_preference(
            self.user, category="meridian", in_app_enabled=False, push_enabled=True,
        )
        services.set_preference(
            self.user, category="meridian", in_app_enabled=True, push_enabled=True,
        )
        note = services.create_notification(self.user, title="T", message="M", category="meridian")
        self.assertIsNotNone(note)

    def test_unknown_category_is_rejected(self):
        with self.assertRaises(ValueError):
            services.set_preference(
                self.user, category="not_a_real_category", in_app_enabled=True, push_enabled=True,
            )


class NotificationPreferenceApiTests(TestCase):
    def setUp(self):
        self.user = _make_user("parent")

    def _login(self):
        self.client.post(
            reverse("auth-pin-login"),
            {"username": "parent", "pin": "1234"}, content_type="application/json",
        )

    def test_list_returns_all_categories_with_documented_defaults(self):
        self._login()
        resp = self.client.get(reverse("notification-preferences"))
        self.assertEqual(resp.status_code, 200)
        rows = {row["category"]: row for row in resp.json()}
        self.assertEqual(len(rows), 12)
        # docs/32 §3: household_activity and wish_price_alerts default push-off; the rest push-on.
        self.assertFalse(rows["household_activity"]["push_enabled"])
        self.assertFalse(rows["wish_price_alerts"]["push_enabled"])
        self.assertTrue(rows["meridian"]["push_enabled"])
        self.assertTrue(all(row["in_app_enabled"] for row in rows.values()))
        self.assertTrue(rows["appointments"]["supports_mine_only"])
        self.assertFalse(rows["corners"]["supports_mine_only"])

    def test_patch_persists_and_is_reflected_on_next_get(self):
        self._login()
        resp = self.client.patch(
            reverse("notification-preferences"),
            [{"category": "meridian", "in_app_enabled": False, "push_enabled": False}],
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200, resp.json())
        rows = {row["category"]: row for row in resp.json()}
        self.assertFalse(rows["meridian"]["in_app_enabled"])
        # Untouched categories keep their defaults, not reset to some blanket value.
        self.assertTrue(rows["fitness"]["in_app_enabled"])

    def test_preferences_are_self_only(self):
        other = _make_user("other", role=User.Role.USER)
        services.set_preference(other, category="meridian", in_app_enabled=False, push_enabled=False)
        self._login()
        resp = self.client.get(reverse("notification-preferences"))
        rows = {row["category"]: row for row in resp.json()}
        self.assertTrue(rows["meridian"]["in_app_enabled"])  # this user's own default, not other's


class NotificationSettingsApiTests(TestCase):
    def setUp(self):
        self.user = _make_user("parent")

    def _login(self):
        self.client.post(
            reverse("auth-pin-login"),
            {"username": "parent", "pin": "1234"}, content_type="application/json",
        )

    def test_get_returns_defaults_before_any_row_exists(self):
        self._login()
        resp = self.client.get(reverse("notification-settings"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsNone(data["quiet_start"])
        self.assertIsNone(data["quiet_end"])
        self.assertEqual(data["morning_time"], "08:00:00")

    def test_patch_updates_quiet_hours(self):
        self._login()
        resp = self.client.patch(
            reverse("notification-settings"),
            {"quiet_start": "22:00", "quiet_end": "07:00"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200, resp.json())
        self.assertEqual(resp.json()["quiet_start"], "22:00:00")
        self.assertEqual(resp.json()["quiet_end"], "07:00:00")


_VAPID_SETTINGS = dict(
    VAPID_PUBLIC_KEY="test-public-key", VAPID_PRIVATE_KEY="test-private-key",
    VAPID_SUBJECT="mailto:test@example.com",
)


class PushDeviceApiTests(TestCase):
    def setUp(self):
        self.user = _make_user("parent")
        self.client.post(
            reverse("auth-pin-login"),
            {"username": "parent", "pin": "1234"}, content_type="application/json",
        )

    def test_vapid_public_key_endpoint(self):
        with override_settings(**_VAPID_SETTINGS):
            resp = self.client.get(reverse("notification-vapid-public-key"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["public_key"], "test-public-key")

    def test_register_list_and_unregister_device(self):
        resp = self.client.post(
            reverse("notification-devices"),
            {"endpoint": "https://push.example/abc", "keys": {"p256dh": "p", "auth": "a"}, "label": "My phone"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201, resp.json())
        device_id = resp.json()["id"]
        listed = self.client.get(reverse("notification-devices"))
        self.assertEqual(len(listed.json()), 1)
        self.assertEqual(listed.json()[0]["label"], "My phone")
        deleted = self.client.delete(reverse("notification-device-detail", args=[device_id]))
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(len(self.client.get(reverse("notification-devices")).json()), 0)

    def test_register_rejects_missing_keys(self):
        resp = self.client.post(
            reverse("notification-devices"),
            {"endpoint": "https://push.example/abc", "keys": {"p256dh": "p"}},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_devices_are_self_only(self):
        other = _make_user("other", role=User.Role.USER)
        services.register_push_device(other, endpoint="https://push.example/theirs", p256dh="p", auth="a")
        resp = self.client.get(reverse("notification-devices"))
        self.assertEqual(resp.json(), [])
        # Can't delete someone else's device by guessing its ID either.
        their_device = PushDevice.objects.get(endpoint="https://push.example/theirs")
        deleted = self.client.delete(reverse("notification-device-detail", args=[their_device.id]))
        self.assertEqual(deleted.status_code, 404)


class PushDeliveryTests(TestCase):
    """docs/32_Core_Notifications_and_Push.md §10 — the actual send path, webpush mocked."""

    def setUp(self):
        self.user = _make_user("parent")
        self.device = PushDevice.objects.create(
            household=self.user.household, user=self.user,
            endpoint="https://push.example/abc", p256dh="p", auth="a",
        )

    def test_push_sent_when_configured_and_enabled(self):
        with override_settings(**_VAPID_SETTINGS), patch("pywebpush.webpush") as mock_webpush:
            services.create_notification(
                self.user, title="T", message="M", category="meridian", source_node="meridian",
            )
        mock_webpush.assert_called_once()

    def test_push_not_sent_without_vapid_configured(self):
        with override_settings(VAPID_PUBLIC_KEY="", VAPID_PRIVATE_KEY=""), \
             patch("pywebpush.webpush") as mock_webpush:
            services.create_notification(
                self.user, title="T", message="M", category="meridian", source_node="meridian",
            )
        mock_webpush.assert_not_called()

    def test_push_not_sent_when_push_disabled(self):
        services.set_preference(self.user, category="meridian", in_app_enabled=True, push_enabled=False)
        with override_settings(**_VAPID_SETTINGS), patch("pywebpush.webpush") as mock_webpush:
            services.create_notification(
                self.user, title="T", message="M", category="meridian", source_node="meridian",
            )
        mock_webpush.assert_not_called()

    def test_push_not_sent_during_quiet_hours(self):
        UserNotificationSettings.objects.create(
            household=self.user.household, user=self.user,
            quiet_start=time(0, 0), quiet_end=time(23, 59),
        )
        with override_settings(**_VAPID_SETTINGS), patch("pywebpush.webpush") as mock_webpush:
            services.create_notification(
                self.user, title="T", message="M", category="meridian", source_node="meridian",
            )
        mock_webpush.assert_not_called()

    def test_sensitive_source_never_pushes(self):
        HouseholdNode.objects.filter(node__key="solace").update(requires_reauthentication=True)
        with override_settings(**_VAPID_SETTINGS), patch("pywebpush.webpush") as mock_webpush:
            services.create_notification(
                self.user, title="T", message="M", category="meridian", source_node="solace",
            )
        mock_webpush.assert_not_called()

    def test_device_deactivated_on_gone_response(self):
        from pywebpush import WebPushException

        class _Resp:
            status_code = 410

        with override_settings(**_VAPID_SETTINGS), \
             patch("pywebpush.webpush", side_effect=WebPushException("gone", response=_Resp())):
            services.create_notification(
                self.user, title="T", message="M", category="meridian", source_node="meridian",
            )
        self.device.refresh_from_db()
        self.assertFalse(self.device.is_active)

    def test_no_devices_means_no_attempt(self):
        self.device.delete()
        with override_settings(**_VAPID_SETTINGS), patch("pywebpush.webpush") as mock_webpush:
            services.create_notification(
                self.user, title="T", message="M", category="meridian", source_node="meridian",
            )
        mock_webpush.assert_not_called()


class PushDeviceTestEndpointTests(TestCase):
    def setUp(self):
        self.user = _make_user("parent")
        self.device = PushDevice.objects.create(
            household=self.user.household, user=self.user,
            endpoint="https://push.example/abc", p256dh="p", auth="a",
        )
        self.client.post(
            reverse("auth-pin-login"),
            {"username": "parent", "pin": "1234"}, content_type="application/json",
        )

    def test_test_push_sends_immediately_bypassing_preferences(self):
        services.set_preference(self.user, category="meridian", in_app_enabled=True, push_enabled=False)
        with override_settings(**_VAPID_SETTINGS), patch("pywebpush.webpush") as mock_webpush:
            resp = self.client.post(reverse("notification-device-test", args=[self.device.id]))
        self.assertEqual(resp.status_code, 200, resp.json())
        self.assertTrue(resp.json()["delivered"])
        mock_webpush.assert_called_once()

    def test_test_push_without_vapid_configured_is_a_clean_error(self):
        with override_settings(VAPID_PUBLIC_KEY="", VAPID_PRIVATE_KEY=""):
            resp = self.client.post(reverse("notification-device-test", args=[self.device.id]))
        self.assertEqual(resp.status_code, 400)
