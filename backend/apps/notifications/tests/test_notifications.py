"""Notifications tests (Milestone 2, Phase 2.15)."""
from datetime import datetime, time, timedelta
from importlib import import_module
from unittest.mock import patch

from django.apps import apps as django_apps
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.atlas.services import (
    create_atlas_list, create_list_item, create_reminder, ensure_household_grocery_list,
)
from apps.books.services import create_personal_entry, update_personal_entry
from apps.core.models import get_active_household
from apps.hub.models import HouseholdHubWidget, HubWidget
from apps.meridian import services as meridian
from apps.nodes.models import HouseholdNode
from apps.notifications import device_naming, selectors, services
from apps.notifications.models import (
    Notification, NotificationReminderLog, PushDevice, UserNotificationSettings,
)
from apps.notifications.tasks import run_countdown_digest, run_due_reminders
from apps.people.models import Person
from apps.scheduling.services import create_event


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

    def test_bulk_read_through_snapshot_does_not_mark_a_later_notification(self):
        first = services.create_notification(self.user, title="First", message="m")
        later = services.create_notification(self.user, title="Arrived later", message="m")
        self._login()
        resp = self.client.post(
            reverse("notification-read-all"),
            {"through_id": first.id},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        first.refresh_from_db()
        later.refresh_from_db()
        self.assertTrue(first.is_read)
        self.assertFalse(later.is_read)
        self.assertEqual(selectors.unread_count(self.user), 1)

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

    def test_current_device_matches_only_the_callers_active_subscription(self):
        mine = services.register_push_device(
            self.user, endpoint="https://push.example/mine", p256dh="p", auth="a",
        )
        other = _make_user("other", role=User.Role.USER)
        services.register_push_device(
            other, endpoint="https://push.example/theirs", p256dh="p", auth="a",
        )

        matched = self.client.post(
            reverse("notification-device-current"),
            {"endpoint": "https://push.example/mine"}, content_type="application/json",
        )
        self.assertEqual(matched.status_code, 200, matched.json())
        self.assertEqual(matched.json(), {"device_id": mine.id})

        not_mine = self.client.post(
            reverse("notification-device-current"),
            {"endpoint": "https://push.example/theirs"}, content_type="application/json",
        )
        self.assertEqual(not_mine.status_code, 200, not_mine.json())
        self.assertEqual(not_mine.json(), {"device_id": None})


_FIREFOX_LINUX = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
)
_CHROME_ANDROID = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Mobile Safari/537.36"
)
_SAFARI_IPHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
)
_EDGE_WINDOWS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0"
)


class DeviceNamingTests(TestCase):
    """docs/32 §4 — the generated friendly name and its secondary technical detail."""

    def test_recognises_common_browser_platform_pairs(self):
        cases = [
            (_FIREFOX_LINUX, ("Firefox", "Linux", "Firefox on Linux")),
            (_CHROME_ANDROID, ("Chrome", "Android", "Chrome on Android")),
            (_SAFARI_IPHONE, ("Safari", "iPhone", "Safari on iPhone")),
            (_EDGE_WINDOWS, ("Edge", "Windows", "Edge on Windows")),
        ]
        for user_agent, expected in cases:
            with self.subTest(user_agent=user_agent):
                self.assertEqual(device_naming.describe(user_agent), expected)

    def test_chromium_derivatives_are_not_reported_as_chrome(self):
        # Edge/Opera/Samsung User-Agents all also contain "Chrome"; the more specific token wins.
        opera = "Mozilla/5.0 (Windows NT 10.0) Chrome/126.0.0.0 Safari/537.36 OPR/112.0.0.0"
        self.assertEqual(device_naming.parse_user_agent(opera)[0], "Opera")

    def test_ios_browsers_are_not_reported_as_safari(self):
        chrome_ios = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) CriOS/126.0.0.0 Mobile/15E148 Safari/604.1"
        )
        self.assertEqual(device_naming.parse_user_agent(chrome_ios), ("Chrome", "iPhone"))

    def test_unknown_user_agent_still_produces_a_usable_name(self):
        self.assertEqual(device_naming.parse_user_agent(""), ("", ""))
        self.assertEqual(device_naming.default_label("", ""), "New device")


class DeviceNamingBackfillTests(TestCase):
    """The notifications.0005 data step, run against real rows rather than an empty table."""

    def setUp(self):
        self.user = _make_user("parent")
        # Migration modules start with a digit, so they can only be reached via importlib.
        self.backfill = import_module(
            "apps.notifications.migrations."
            "0005_pushdevice_browser_pushdevice_label_is_custom_and_more"
        ).backfill_device_naming

    def _device(self, endpoint, label, user_agent):
        return PushDevice.objects.create(
            household=self.user.household, user=self.user, endpoint=endpoint,
            p256dh="p", auth="a", label=label, user_agent=user_agent,
        )

    def test_regenerates_old_client_side_names_but_keeps_real_ones(self):
        legacy = self._device("https://push.example/1", "This device", _FIREFOX_LINUX)
        chosen = self._device("https://push.example/2", "Kitchen Tablet", _CHROME_ANDROID)

        self.backfill(django_apps, None)

        legacy.refresh_from_db()
        self.assertEqual(legacy.label, "Firefox on Linux")
        self.assertFalse(legacy.label_is_custom)
        self.assertEqual((legacy.browser, legacy.platform), ("Firefox", "Linux"))

        chosen.refresh_from_db()
        self.assertEqual(chosen.label, "Kitchen Tablet")
        self.assertTrue(chosen.label_is_custom)
        self.assertEqual(chosen.platform, "Android")


class PushDeviceNamingApiTests(TestCase):
    """Registration names the device server-side; the owner can rename it afterwards."""

    def setUp(self):
        self.user = _make_user("parent")
        self.client.post(
            reverse("auth-pin-login"),
            {"username": "parent", "pin": "1234"}, content_type="application/json",
        )

    def _register(self, endpoint="https://push.example/abc", user_agent=_FIREFOX_LINUX, **extra):
        return self.client.post(
            reverse("notification-devices"),
            {"endpoint": endpoint, "keys": {"p256dh": "p", "auth": "a"}, **extra},
            content_type="application/json", HTTP_USER_AGENT=user_agent,
        )

    def test_registration_generates_a_name_from_the_user_agent(self):
        body = self._register(user_agent=_CHROME_ANDROID).json()
        self.assertEqual(body["label"], "Chrome on Android")
        self.assertEqual((body["browser"], body["platform"]), ("Chrome", "Android"))
        self.assertFalse(body["label_is_custom"])

    def test_owner_can_rename_a_device(self):
        device_id = self._register().json()["id"]
        resp = self.client.patch(
            reverse("notification-device-detail", args=[device_id]),
            {"label": "  Nick's Laptop  "}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200, resp.json())
        self.assertEqual(resp.json()["label"], "Nick's Laptop")
        self.assertTrue(resp.json()["label_is_custom"])

    def test_blank_rename_restores_the_generated_name(self):
        device_id = self._register().json()["id"]
        self.client.patch(
            reverse("notification-device-detail", args=[device_id]),
            {"label": "Nick's Laptop"}, content_type="application/json",
        )
        resp = self.client.patch(
            reverse("notification-device-detail", args=[device_id]),
            {"label": ""}, content_type="application/json",
        )
        self.assertEqual(resp.json()["label"], "Firefox on Linux")
        self.assertFalse(resp.json()["label_is_custom"])

    def test_re_registering_keeps_a_custom_name_but_refreshes_detail(self):
        device_id = self._register().json()["id"]
        self.client.patch(
            reverse("notification-device-detail", args=[device_id]),
            {"label": "Nick's Laptop"}, content_type="application/json",
        )
        # Same browser subscribes again (e.g. push re-enabled after a permission reset).
        body = self._register().json()
        self.assertEqual(body["id"], device_id)
        self.assertEqual(body["label"], "Nick's Laptop")
        self.assertEqual(body["browser"], "Firefox")

    def test_re_registering_refreshes_a_generated_name(self):
        self._register()
        body = self._register(user_agent=_CHROME_ANDROID).json()
        self.assertEqual(body["label"], "Chrome on Android")

    def test_cannot_rename_someone_elses_device(self):
        other = _make_user("other", role=User.Role.USER)
        services.register_push_device(other, endpoint="https://push.example/theirs", p256dh="p", auth="a")
        theirs = PushDevice.objects.get(endpoint="https://push.example/theirs")
        resp = self.client.patch(
            reverse("notification-device-detail", args=[theirs.id]),
            {"label": "Mine now"}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 404)
        theirs.refresh_from_db()
        self.assertNotEqual(theirs.label, "Mine now")

    def test_device_response_never_exposes_subscription_secrets(self):
        body = self._register().json()
        for secret in ("endpoint", "p256dh", "auth", "keys"):
            self.assertNotIn(secret, body)


class HouseholdPushDeviceOverviewTests(TestCase):
    """docs/32 §7 — admin-only read of every household device, grouped by owner."""

    def setUp(self):
        self.admin = _make_user("admin")
        self.member = _make_user("member", role=User.Role.USER)
        services.register_push_device(
            self.admin, endpoint="https://push.example/admin-laptop",
            p256dh="p", auth="a", user_agent=_FIREFOX_LINUX,
        )
        services.register_push_device(
            self.member, endpoint="https://push.example/member-phone",
            p256dh="p", auth="a", user_agent=_SAFARI_IPHONE,
        )

    def _login(self, username):
        self.client.post(
            reverse("auth-pin-login"),
            {"username": username, "pin": "1234"}, content_type="application/json",
        )

    def test_admin_sees_every_users_devices_grouped(self):
        self._login("admin")
        resp = self.client.get(reverse("notification-household-devices"))
        self.assertEqual(resp.status_code, 200)
        groups = {row["user_display_name"]: row for row in resp.json()}
        self.assertEqual(set(groups), {"Admin", "Member"})
        self.assertEqual(groups["Member"]["devices"][0]["label"], "Safari on iPhone")
        self.assertEqual(groups["Admin"]["devices"][0]["browser"], "Firefox")

    def test_non_admin_is_denied(self):
        self._login("member")
        resp = self.client.get(reverse("notification-household-devices"))
        self.assertEqual(resp.status_code, 403)

    def test_overview_omits_revoked_devices(self):
        PushDevice.objects.filter(user=self.member).update(is_active=False)
        self._login("admin")
        resp = self.client.get(reverse("notification-household-devices"))
        self.assertEqual([row["user_display_name"] for row in resp.json()], ["Admin"])

    def test_overview_never_exposes_subscription_secrets(self):
        self._login("admin")
        devices = [d for row in self.client.get(
            reverse("notification-household-devices")
        ).json() for d in row["devices"]]
        self.assertTrue(devices)
        for device in devices:
            for secret in ("endpoint", "p256dh", "auth", "keys"):
                self.assertNotIn(secret, device)


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


class HouseholdActivityDispatcherTests(TestCase):
    """docs/32_Core_Notifications_and_Push.md §7 — event bus -> notification, visibility-safe."""

    def setUp(self):
        self.actor = _make_user("actor", role=User.Role.USER)
        self.other = _make_user("other", role=User.Role.USER)

    def _unread_for(self, user, source_node):
        return Notification.objects.filter(recipient_user=user, source_node=source_node, is_read=False)

    def test_calendar_event_creation_notifies_other_household_members(self):
        create_event(self.actor, title="Dentist", start_at=timezone.now())
        notes = self._unread_for(self.other, "scheduling")
        self.assertEqual(notes.count(), 1)
        self.assertIn("Dentist", notes.first().message)

    def test_calendar_event_creator_is_not_notified(self):
        create_event(self.actor, title="Dentist", start_at=timezone.now())
        self.assertEqual(self._unread_for(self.actor, "scheduling").count(), 0)

    def test_a_calendar_addition_pushes_without_anyone_changing_a_preference(self):
        """Adding to the shared calendar is an `appointments` notification, which pushes by
        default — it used to be `household_activity`, whose default is push off (docs/32 §4), so
        a partner adding an appointment produced a silent in-app row and nothing on the phone."""
        PushDevice.objects.create(
            household=self.other.household, user=self.other,
            endpoint="https://push.example/other", p256dh="p", auth="a",
        )
        with override_settings(**_VAPID_SETTINGS), \
                patch("apps.notifications.push._send_to_device") as send:
            create_event(self.actor, title="Dentist", start_at=timezone.now())
        self.assertEqual(send.call_count, 1)

    def test_a_shopping_list_addition_still_stays_quiet_by_default(self):
        # The noisy half of household_activity keeps its quieter default.
        PushDevice.objects.create(
            household=self.other.household, user=self.other,
            endpoint="https://push.example/other", p256dh="p", auth="a",
        )
        atlas_list = ensure_household_grocery_list(self.actor)
        with override_settings(**_VAPID_SETTINGS), \
                patch("apps.notifications.push._send_to_device") as send:
            create_list_item(self.actor, atlas_list, title="Milk")
        self.assertEqual(send.call_count, 0)

    def test_private_calendar_event_does_not_notify_others(self):
        create_event(self.actor, title="Secret", start_at=timezone.now(), visibility="private")
        self.assertEqual(self._unread_for(self.other, "scheduling").count(), 0)

    def test_calendar_event_hidden_from_a_user_excludes_them(self):
        create_event(self.actor, title="Surprise", start_at=timezone.now(), hidden_from_users=[self.other])
        self.assertEqual(self._unread_for(self.other, "scheduling").count(), 0)

    def test_atlas_list_additions_are_bundled_not_spammed(self):
        atlas_list = ensure_household_grocery_list(self.actor)
        create_list_item(self.actor, atlas_list, title="Milk")
        create_list_item(self.actor, atlas_list, title="Eggs")
        create_list_item(self.actor, atlas_list, title="Bread")
        notes = self._unread_for(self.other, "atlas")
        self.assertEqual(notes.count(), 1)
        self.assertIn("Grocery", notes.first().title)
        self.assertEqual(notes.first().message, "Bread")  # updated in place to the latest addition

    def test_private_atlas_list_does_not_notify_others(self):
        atlas_list = create_atlas_list(self.actor, title="My wishlist", visibility="private")
        create_list_item(self.actor, atlas_list, title="Something")
        self.assertEqual(self._unread_for(self.other, "atlas").count(), 0)

    def test_finishing_a_book_notifies_the_household(self):
        entry = create_personal_entry(self.actor, book={"title": "Dune"}, status="reading")
        update_personal_entry(self.actor, entry, status="history")
        notes = self._unread_for(self.other, "books")
        self.assertEqual(notes.count(), 1)
        self.assertEqual(notes.first().message, "Dune")

    def test_moving_within_history_does_not_renotify(self):
        entry = create_personal_entry(self.actor, book={"title": "Dune"}, status="reading")
        update_personal_entry(self.actor, entry, status="history")
        services.mark_all_read(self.other)
        update_personal_entry(self.actor, entry, status="history", position=1)
        self.assertEqual(self._unread_for(self.other, "books").count(), 0)

    def test_creating_directly_into_history_notifies(self):
        create_personal_entry(self.actor, book={"title": "Dune"}, status="history")
        self.assertEqual(self._unread_for(self.other, "books").count(), 1)

    def test_disabling_household_activity_suppresses_its_sources(self):
        services.set_preference(self.other, category="household_activity", in_app_enabled=False, push_enabled=False)
        atlas_list = ensure_household_grocery_list(self.actor)
        create_list_item(self.actor, atlas_list, title="Milk")
        create_personal_entry(self.actor, book={"title": "Dune"}, status="history")
        self.assertEqual(Notification.objects.filter(recipient_user=self.other, is_read=False).count(), 0)

    def test_calendar_additions_follow_appointments_not_household_activity(self):
        # Someone who has muted list chatter should still hear about a new appointment; muting
        # appointments is what silences the calendar.
        services.set_preference(self.other, category="household_activity", in_app_enabled=False, push_enabled=False)
        create_event(self.actor, title="Dentist", start_at=timezone.now())
        self.assertEqual(self._unread_for(self.other, "scheduling").count(), 1)

        services.set_preference(self.other, category="appointments", in_app_enabled=False, push_enabled=False)
        create_event(self.actor, title="Physio", start_at=timezone.now())
        self.assertEqual(self._unread_for(self.other, "scheduling").count(), 1)


class ScheduledReminderTests(TestCase):
    """docs/32_Core_Notifications_and_Push.md §8 — 24h-before + morning-of reminders."""

    def setUp(self):
        self.parent = _make_user("parent", role=User.Role.USER)
        self.other = _make_user("other", role=User.Role.USER)

    def test_24h_before_appointment_notifies_household(self):
        due = timezone.now() + timedelta(hours=24)
        create_event(self.parent, title="Dentist", start_at=due)
        result = run_due_reminders()
        self.assertEqual(result["24h"], 1)
        for user in (self.parent, self.other):
            notes = Notification.objects.filter(
                recipient_user=user, source_node="scheduling", title="Tomorrow",
            )
            self.assertEqual(notes.count(), 1)
            self.assertEqual(notes.first().message, "Dentist")

    def test_24h_reminder_is_idempotent(self):
        due = timezone.now() + timedelta(hours=24)
        create_event(self.parent, title="Dentist", start_at=due)
        run_due_reminders()
        run_due_reminders()
        self.assertEqual(
            Notification.objects.filter(source_node="scheduling", title="Tomorrow").count(), 2,
        )

    def test_event_outside_24h_window_is_not_reminded(self):
        due = timezone.now() + timedelta(hours=30)
        create_event(self.parent, title="Later", start_at=due)
        result = run_due_reminders()
        self.assertEqual(result["24h"], 0)

    def test_a_todo_is_notified_by_its_own_offsets_not_the_fixed_sweep(self):
        """A To-do's notifications are its ``notify_offsets`` and nothing else (D19 §F).

        Regression for the v0.40 integration: a To-do's due date syncs an Atlas-sourced calendar
        event, which the fixed 24h/morning-of sweep here used to pick up as well. A household
        that selected "1 day before" would then have been told twice about the same occurrence
        — once by this sweep and once by run_due_todo_offsets.
        """
        from apps.notifications.tasks import run_due_todo_offsets

        atlas_list = create_atlas_list(self.parent, title="Chores", list_type="todo")
        due = timezone.now() + timedelta(hours=24)
        create_list_item(
            self.parent, atlas_list, title="Take out bins", due_at=due, notify_offsets=[1440],
        )

        self.assertEqual(run_due_reminders()["24h"], 0)
        self.assertFalse(
            Notification.objects.filter(source_node="atlas", title="Due tomorrow").exists()
        )

        self.assertEqual(run_due_todo_offsets(), 1)
        notes = Notification.objects.filter(
            recipient_user=self.other, source_node="atlas", title="Due in 1 day",
        )
        self.assertEqual(notes.count(), 1)
        self.assertEqual(notes.first().message, "Take out bins")

    def test_a_todo_with_no_offsets_is_not_notified_at_all(self):
        """Empty ``notify_offsets`` means "no notifications" (the field's own contract) — the
        fixed sweep must not quietly reinstate one."""
        from apps.notifications.tasks import run_due_todo_offsets

        atlas_list = create_atlas_list(self.parent, title="Chores", list_type="todo")
        due = timezone.now() + timedelta(hours=24)
        create_list_item(self.parent, atlas_list, title="Silent job", due_at=due)

        run_due_reminders()
        run_due_todo_offsets()
        # "Actor added Silent job" household-activity notifications are a different feature and
        # are expected; what must not exist is any *scheduled reminder* for this item.
        self.assertFalse(
            Notification.objects.filter(message="Silent job", title__startswith="Due").exists()
        )
        self.assertFalse(NotificationReminderLog.objects.filter(record_type="AtlasListItem").exists())

    def test_scheduled_reminder_notifies_only_its_selected_recipient(self):
        recipient = _make_person("Other", linked_user=self.other)
        due = timezone.now() + timedelta(hours=24)
        create_reminder(
            self.parent,
            title="Take medicine",
            due_at=due,
            assigned_to_people=[recipient],
            notifications_enabled=True,
        )
        run_due_reminders()
        self.assertTrue(Notification.objects.filter(
            recipient_user=self.other, source_node="atlas", message="Take medicine",
        ).exists())
        self.assertFalse(Notification.objects.filter(
            recipient_user=self.parent, source_node="atlas", message="Take medicine",
        ).exists())

    def test_disabled_scheduled_reminder_sends_nothing(self):
        due = timezone.now() + timedelta(hours=24)
        create_reminder(
            self.parent,
            title="Silent reminder",
            due_at=due,
            notifications_enabled=False,
        )
        result = run_due_reminders()
        self.assertEqual(result["24h"], 0)
        self.assertFalse(Notification.objects.filter(message="Silent reminder").exists())

    def test_appointment_is_never_worded_as_due_or_overdue(self):
        """An appointment happens, it is not "due" — docs/32 §8.

        This is the regression the owner reported: a Brewoomba appointment announced as
        "Due today". Bills and tasks own that wording; events and appointments never do.
        """
        today = timezone.now().date()
        due_at = timezone.make_aware(datetime.combine(today, time(15, 0)))
        create_event(self.parent, title="Brewoomba", start_at=due_at, event_kind="appointment")
        run_due_reminders(now=timezone.make_aware(datetime.combine(today, time(8, 0))))
        tomorrow_at = timezone.now() + timedelta(hours=24)
        create_event(self.parent, title="Hairdresser", start_at=tomorrow_at, event_kind="appointment")
        run_due_reminders()

        titles = set(
            Notification.objects.filter(source_node="scheduling").values_list("title", flat=True)
        )
        self.assertTrue(titles)
        for title in titles:
            self.assertNotIn("Due", title)
            self.assertNotIn("Overdue", title)
        self.assertIn("Starts at 3:00 PM", titles)
        self.assertIn("Tomorrow", titles)

    def test_reminder_uses_reminder_wording_not_due_wording(self):
        due = timezone.now() + timedelta(hours=24)
        create_reminder(self.parent, title="Water the plants", due_at=due)
        run_due_reminders()
        self.assertTrue(Notification.objects.filter(
            source_node="atlas", title="Reminder tomorrow", message="Water the plants",
        ).exists())

    # Pinned away from the 08:00 default morning_time so the morning-of lead cannot also fire
    # and make these counts depend on the wall-clock hour the suite happens to run at.
    def _midday(self):
        return timezone.make_aware(datetime.combine(timezone.now().date(), time(13, 0)))

    def test_reminder_notifies_at_its_scheduled_time(self):
        now = self._midday()
        create_reminder(self.parent, title="Take medicine", due_at=now - timedelta(minutes=5))
        result = run_due_reminders(now=now)
        self.assertEqual(result["due_at"], 1)
        titles = set(Notification.objects.filter(
            source_node="atlas", message="Take medicine",
        ).values_list("title", flat=True))
        self.assertEqual(titles, {"Reminder"})

    def test_scheduled_time_delivery_is_idempotent(self):
        now = self._midday()
        create_reminder(self.parent, title="Take medicine", due_at=now - timedelta(minutes=5))
        run_due_reminders(now=now)
        run_due_reminders(now=now)
        self.assertEqual(
            Notification.objects.filter(
                source_node="atlas", message="Take medicine", title="Reminder",
            ).count(),
            2,  # one per household member, not one per sweep
        )

    def test_long_past_reminder_is_not_resurrected(self):
        now = self._midday()
        create_reminder(self.parent, title="Ancient", due_at=now - timedelta(days=3))
        result = run_due_reminders(now=now)
        self.assertEqual(result["due_at"], 0)
        self.assertFalse(Notification.objects.filter(message="Ancient").exists())

    def test_mine_only_preference_skips_unassigned_events(self):
        services.set_preference(
            self.other, category="appointments", in_app_enabled=True, push_enabled=True, mine_only=True,
        )
        due = timezone.now() + timedelta(hours=24)
        create_event(self.parent, title="Dentist", start_at=due)
        run_due_reminders()
        self.assertEqual(
            Notification.objects.filter(
                recipient_user=self.other, source_node="scheduling", title="Tomorrow",
            ).count(),
            0,
        )

    def test_mine_only_still_notifies_when_assigned(self):
        person = _make_person("Other", linked_user=self.other)
        services.set_preference(
            self.other, category="appointments", in_app_enabled=True, push_enabled=True, mine_only=True,
        )
        due = timezone.now() + timedelta(hours=24)
        create_event(self.parent, title="Dentist", start_at=due, assigned_to_people=[person.id])
        run_due_reminders()
        self.assertEqual(
            Notification.objects.filter(
                recipient_user=self.other, source_node="scheduling", title="Tomorrow",
            ).count(),
            1,
        )

    def test_disabled_category_receives_no_reminder(self):
        services.set_preference(
            self.other, category="appointments", in_app_enabled=False, push_enabled=False, mine_only=False,
        )
        due = timezone.now() + timedelta(hours=24)
        create_event(self.parent, title="Dentist", start_at=due)
        run_due_reminders()
        self.assertEqual(
            Notification.objects.filter(
                recipient_user=self.other, source_node="scheduling", title="Tomorrow",
            ).count(),
            0,
        )

    def test_morning_of_notifies_at_users_morning_time(self):
        today = timezone.now().date()
        due_at = timezone.make_aware(datetime.combine(today, time(15, 0)))
        create_event(self.parent, title="Dentist", start_at=due_at)
        morning_now = timezone.make_aware(datetime.combine(today, time(8, 0)))
        result = run_due_reminders(now=morning_now)
        self.assertEqual(result["morning_of"], 2)
        notes = Notification.objects.filter(
            recipient_user=self.other, source_node="scheduling", title="Starts at 3:00 PM",
        )
        self.assertEqual(notes.count(), 1)

    def test_morning_of_respects_per_user_morning_time(self):
        services.update_settings(self.other, morning_time=time(9, 0))
        today = timezone.now().date()
        due_at = timezone.make_aware(datetime.combine(today, time(15, 0)))
        create_event(self.parent, title="Dentist", start_at=due_at)
        eight_am = timezone.make_aware(datetime.combine(today, time(8, 0)))
        run_due_reminders(now=eight_am)
        self.assertEqual(
            Notification.objects.filter(recipient_user=self.other, source_node="scheduling", title="Starts at 3:00 PM").count(), 0,
        )
        nine_am = timezone.make_aware(datetime.combine(today, time(9, 0)))
        run_due_reminders(now=nine_am)
        self.assertEqual(
            Notification.objects.filter(recipient_user=self.other, source_node="scheduling", title="Starts at 3:00 PM").count(), 1,
        )

    def test_morning_of_is_idempotent_per_user(self):
        today = timezone.now().date()
        due_at = timezone.make_aware(datetime.combine(today, time(15, 0)))
        create_event(self.parent, title="Dentist", start_at=due_at)
        morning_now = timezone.make_aware(datetime.combine(today, time(8, 0)))
        run_due_reminders(now=morning_now)
        run_due_reminders(now=morning_now)
        self.assertEqual(
            Notification.objects.filter(recipient_user=self.other, source_node="scheduling", title="Starts at 3:00 PM").count(), 1,
        )


class CountdownDigestTests(TestCase):
    """docs/32_Core_Notifications_and_Push.md §9 — daily countdown digest."""

    def setUp(self):
        self.parent = _make_user("parent", role=User.Role.USER)
        self.other = _make_user("other", role=User.Role.USER)

    def _enable_countdown(self, *, target_date, target_time="12:00"):
        widget = HubWidget.objects.get(key="countdown")
        return HouseholdHubWidget.objects.create(
            household=get_active_household(), widget=widget, is_enabled=True,
            settings_json={"title": "Trip", "target_date": target_date, "target_time": target_time},
        )

    def test_countdown_digest_sends_to_everyone_at_their_morning_time(self):
        target_date = (timezone.now() + timedelta(days=5)).date().isoformat()
        self._enable_countdown(target_date=target_date)
        morning_now = timezone.make_aware(datetime.combine(timezone.now().date(), time(8, 0)))
        result = run_countdown_digest(now=morning_now)
        self.assertEqual(result["sent"], 2)
        note = Notification.objects.get(recipient_user=self.other, source_node="hub")
        self.assertIn("day", note.message)

    def test_countdown_digest_is_idempotent_same_day(self):
        target_date = (timezone.now() + timedelta(days=5)).date().isoformat()
        self._enable_countdown(target_date=target_date)
        morning_now = timezone.make_aware(datetime.combine(timezone.now().date(), time(8, 0)))
        run_countdown_digest(now=morning_now)
        run_countdown_digest(now=morning_now)
        self.assertEqual(Notification.objects.filter(source_node="hub").count(), 2)

    def test_no_countdown_widget_sends_nothing(self):
        result = run_countdown_digest()
        self.assertEqual(result["sent"], 0)

    def test_disabled_countdown_widget_sends_nothing(self):
        target_date = (timezone.now() + timedelta(days=5)).date().isoformat()
        widget_row = self._enable_countdown(target_date=target_date)
        widget_row.is_enabled = False
        widget_row.save(update_fields=["is_enabled"])
        result = run_countdown_digest()
        self.assertEqual(result["sent"], 0)

    def test_past_target_date_sends_nothing(self):
        target_date = (timezone.now() - timedelta(days=1)).date().isoformat()
        self._enable_countdown(target_date=target_date)
        result = run_countdown_digest()
        self.assertEqual(result["sent"], 0)

    def test_countdown_disabled_category_is_skipped(self):
        services.set_preference(
            self.other, category="countdown", in_app_enabled=False, push_enabled=False, mine_only=False,
        )
        target_date = (timezone.now() + timedelta(days=5)).date().isoformat()
        self._enable_countdown(target_date=target_date)
        morning_now = timezone.make_aware(datetime.combine(timezone.now().date(), time(8, 0)))
        run_countdown_digest(now=morning_now)
        self.assertEqual(Notification.objects.filter(recipient_user=self.other, source_node="hub").count(), 0)
