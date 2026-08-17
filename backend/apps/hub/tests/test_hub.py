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
from apps.permissions.services import grant_user_permission
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


def _reauth(client, password="pass123!"):
    client.post(
        reverse("auth-reauth"),
        {"password": password},
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

    def _keys(self, url_name="hub"):
        return [w["key"] for w in self.client.get(reverse(url_name)).json()["widgets"]]

    def _widget(self, key, url_name="hub"):
        """The named widget, or None when the Hub dropped it for having nothing to show."""
        return next(
            (w for w in self.client.get(reverse(url_name)).json()["widgets"] if w["key"] == key),
            None,
        )

    def test_hub_contains_atlas_todos_widget_once_it_has_content(self):
        atlas_list = create_atlas_list(self.admin, title="Chores", list_type="todo")
        create_list_item(self.admin, atlas_list, title="Clean bathroom")
        self.assertIn("atlas_todos", self._keys())

    def test_empty_widget_is_dropped_from_the_hub(self):
        """An empty card spends a grid slot to say nothing — it must not be returned."""
        self.assertNotIn("atlas_todos", self._keys())

    def test_ambient_widgets_survive_being_empty(self):
        """Clock/quick add own no domain data; suppressing them would empty the Hub."""
        keys = self._keys()
        self.assertIn("clock", keys)
        self.assertIn("quick_add", keys)

    def test_disabled_stack_hides_its_widgets(self):
        from apps.meridian.services import create_task
        from apps.nodes.services import disable_node

        create_task(self.admin, title="Tidy the lounge", points=5)
        self.assertTrue(
            any(k.startswith("meridian_") for k in self._keys()),
            "meridian widgets expected while enabled",
        )
        disable_node(self.admin, "meridian")
        self.assertFalse(
            any(k.startswith("meridian_") for k in self._keys()),
            "meridian widgets should vanish when stack disabled",
        )

    def test_todos_widget_includes_open_items(self):
        atlas_list = create_atlas_list(self.admin, title="Chores", list_type="todo")
        create_list_item(self.admin, atlas_list, title="Clean bathroom")
        resp = self.client.get(reverse("hub"))
        todos = next(w for w in resp.json()["widgets"] if w["key"] == "atlas_todos")
        item_titles = [i["title"] for i in todos["items"]]
        self.assertIn("Clean bathroom", item_titles)

    def test_todos_widget_is_dropped_when_every_item_is_complete(self):
        from apps.atlas.services import complete_list_item
        atlas_list = create_atlas_list(self.admin, title="Tasks", list_type="todo")
        item = create_list_item(self.admin, atlas_list, title="Done task")
        complete_list_item(self.admin, item)
        self.assertIsNone(self._widget("atlas_todos"))

    def test_todos_widget_hides_items_from_private_list_for_child(self):
        _make_user("child", User.Role.USER, is_child=True)
        shared = create_atlas_list(self.admin, title="Shared tasks", list_type="todo")
        create_list_item(self.admin, shared, title="Visible task")
        private_list = create_atlas_list(
            self.admin, title="Private tasks", list_type="todo", visibility=AtlasVisibility.PRIVATE
        )
        create_list_item(self.admin, private_list, title="Hidden task")
        _login(self.client, "child")
        todos = self._widget("atlas_todos")
        self.assertIsNotNone(todos)
        titles = [i["title"] for i in todos["items"]]
        self.assertIn("Visible task", titles)
        self.assertNotIn("Hidden task", titles)


class UpcomingWidgetTests(TestCase):
    """The unified Upcoming widget — one card for everything dated (owner, 2026-08-09).

    It reads calendar events, which already mirror every dated node record via the
    scheduling helper (D7), so a record must appear exactly once however many nodes
    contributed it.
    """

    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        _login(self.client, "admin")

    def _upcoming(self):
        return next(
            (w for w in self.client.get(reverse("hub")).json()["widgets"] if w["key"] == "upcoming"),
            None,
        )

    def _widget(self, key):
        return next(
            (widget for widget in self.client.get(reverse("hub")).json()["widgets"] if widget["key"] == key),
            None,
        )

    def test_includes_a_dated_reminder(self):
        create_reminder(self.admin, title="Doctor visit", due_at=_future(48))
        self.assertIn("Doctor visit", [i["title"] for i in self._upcoming()["items"]])

    def test_dated_record_appears_exactly_once(self):
        reminder = create_reminder(self.admin, title="Book dentist", due_at=_future(36))
        self.assertIsNotNone(reminder.calendar_event_id)
        self.assertEqual(
            CalendarEvent.objects.filter(
                source_record_type="AtlasReminder", source_record_id=reminder.id
            ).count(),
            1,
        )
        titles = [i["title"] for i in self._upcoming()["items"]]
        self.assertEqual(titles.count("Book dentist"), 1)

    def test_excludes_beyond_the_fetch_window(self):
        create_reminder(self.admin, title="Next year", due_at=_future(hours=24 * 200))
        self.assertIsNone(self._upcoming(), "a lone far-future item leaves nothing to show")

    def test_aggregates_more_than_one_node(self):
        from apps.pets.services import create_appointment, create_pet

        create_reminder(self.admin, title="Doctor visit", due_at=_future(48))
        pet = create_pet(self.admin, name="Allan", species="cat")
        create_appointment(self.admin, pet=pet, title="Annual vaccination", start_at=_future(72))
        titles = [i["title"] for i in self._upcoming()["items"]]
        self.assertIn("Doctor visit", titles)
        self.assertIn("Allan: Annual vaccination", titles)

    def test_overdue_due_type_record_is_kept(self):
        """A missed reminder still needs attention, so it survives its own due date."""
        create_reminder(self.admin, title="Overdue thing", due_at=_future(hours=-72))
        self.assertIn("Overdue thing", [i["title"] for i in self._upcoming()["items"]])

    def test_past_standalone_event_is_dropped(self):
        """A party last Tuesday is history, not something coming up."""
        from apps.scheduling.services import create_event

        create_event(self.admin, title="Last week's party", start_at=_future(hours=-72))
        self.assertIsNone(self._upcoming())

    def test_today_appointment_is_included(self):
        from apps.pets.services import create_appointment, create_pet

        pet = create_pet(self.admin, name="Allan", species="cat")
        create_appointment(self.admin, pet=pet, title="Vet check", start_at=_future(1))
        self.assertIn("Allan: Vet check", [i["title"] for i in self._upcoming()["items"]])

    def test_tomorrow_appointment_is_included(self):
        from apps.pets.services import create_appointment, create_pet

        pet = create_pet(self.admin, name="Allan", species="cat")
        create_appointment(self.admin, pet=pet, title="Grooming", start_at=_future(24))
        self.assertIn("Allan: Grooming", [i["title"] for i in self._upcoming()["items"]])

    def test_future_appointment_is_included(self):
        from apps.pets.services import create_appointment, create_pet

        pet = create_pet(self.admin, name="Allan", species="cat")
        create_appointment(self.admin, pet=pet, title="Dental", start_at=_future(72))
        self.assertIn("Allan: Dental", [i["title"] for i in self._upcoming()["items"]])

    def test_past_appointment_is_dropped(self):
        from apps.pets.services import create_appointment, create_pet

        pet = create_pet(self.admin, name="Allan", species="cat")
        create_appointment(self.admin, pet=pet, title="Old appointment", start_at=_future(-72))
        self.assertIsNone(self._upcoming())

    def test_overdue_task_is_kept(self):
        from apps.meridian.services import create_task

        create_task(self.admin, title="Overdue task", points=5, due_at=_future(-48))
        self.assertIn("Overdue task", [i["title"] for i in self._upcoming()["items"]])

    def test_overdue_unpaid_bill_is_kept_after_reauth(self):
        from apps.nodes.services import enable_node
        from apps.solace.services import create_bill

        enable_node(self.admin, "solace")
        grant_user_permission(self.admin, "solace.view")
        create_bill(self.admin, name="Overdue electricity", amount="120.00", due_at=_future(-48))
        _reauth(self.client)
        self.assertIn("Bill: Overdue electricity", [i["title"] for i in self._upcoming()["items"]])

    def test_paid_recurring_bill_uses_next_unpaid_occurrence(self):
        from apps.nodes.services import enable_node
        from apps.hub.models import HouseholdHubWidget, HubWidget
        from apps.hub.services import _solace_bills_due_widget
        from apps.solace.services import create_payday
        from apps.solace.models import BillOccurrence
        from apps.solace.services import create_bill, mark_occurrence_paid

        enable_node(self.admin, "solace")
        widget = HubWidget.objects.get(key="solace_bills_due")
        HouseholdHubWidget.objects.get_or_create(
            household=self.admin.household,
            widget=widget,
            defaults={"is_enabled": True, "display_order": 1, "size": "small"},
        )
        bill = create_bill(
            self.admin,
            name="Internet",
            amount="89.00",
            due_at=_future(-48),
            recurrence_rule="FREQ=WEEKLY",
        )
        create_payday(
            self.admin, title="Pay", expected_amount="1000.00", pay_at=_future(480),
            recurrence_rule="FREQ=WEEKLY",
        )
        stale = BillOccurrence.objects.filter(bill=bill, status=BillOccurrence.Status.UPCOMING).order_by("due_at").first()
        self.assertIsNotNone(stale)
        mark_occurrence_paid(self.admin, stale)
        rows, meta = _solace_bills_due_widget(self.admin)
        row = next(item for item in rows if item["bill_name"] == "Internet")
        self.assertFalse(row["is_overdue"])
        self.assertNotEqual(row["id"], stale.id)
        self.assertEqual(meta["bill_count"], len(rows))

    def test_due_before_payday_widget_uses_occurrences_and_keeps_overdue_unpaid(self):
        from apps.nodes.services import enable_node
        from apps.solace.services import create_bill, create_payday, mark_occurrence_unpaid

        enable_node(self.admin, "solace")
        grant_user_permission(self.admin, "solace.view")
        create_payday(
            self.admin, title="Pay", expected_amount="1000.00", pay_at=_future(120),
            recurrence_rule="FREQ=WEEKLY",
        )
        overdue_bill = create_bill(self.admin, name="Overdue", amount="25.00", due_at=_future(-48))
        overdue_occurrence = overdue_bill.occurrences.order_by("due_at").first()
        mark_occurrence_unpaid(self.admin, overdue_occurrence)
        create_bill(self.admin, name="Before pay", amount="40.00", due_at=_future(48))
        create_bill(self.admin, name="After pay", amount="90.00", due_at=_future(168))
        _reauth(self.client)
        widget = self._widget("solace_bills_due")
        self.assertIsNotNone(widget)
        self.assertEqual([row["bill_name"] for row in widget["items"]], ["Overdue", "Before pay"])
        self.assertEqual(widget["meta"]["bill_count"], 2)
        self.assertEqual(widget["meta"]["total"], "65.00")
        self.assertEqual(widget["meta"]["overdue_count"], 1)

    def test_due_before_payday_widget_has_configuration_state_without_income(self):
        from apps.nodes.services import enable_node

        enable_node(self.admin, "solace")
        grant_user_permission(self.admin, "solace.view")
        _reauth(self.client)
        widget = self._widget("solace_bills_due")
        self.assertIsNotNone(widget)
        self.assertFalse(widget["meta"]["configured"])
        self.assertIsNone(widget["meta"]["next_payday"])

    def test_meta_offers_horizons(self):
        create_reminder(self.admin, title="Doctor visit", due_at=_future(48))
        meta = self._upcoming()["meta"]
        self.assertEqual(meta["default_horizon"], "week")
        self.assertIn("week", [h["key"] for h in meta["horizons"]])
        self.assertIn("month", [h["key"] for h in meta["horizons"]])

    def test_financial_events_stay_hidden_until_reauth(self):
        from apps.nodes.services import enable_node
        from apps.solace.services import create_bill

        enable_node(self.admin, "solace")
        create_bill(self.admin, name="Electricity", amount="120.00", due_at=_future(48))
        titles = [i["title"] for i in (self._upcoming() or {"items": []})["items"]]
        self.assertNotIn("Electricity", titles)

    def test_kiosk_hub_returns_kiosk_safe_widgets_only(self):
        resp = self.client.get(reverse("kiosk-hub"))
        for widget in resp.json()["widgets"]:
            self.assertTrue(widget["supports_kiosk"])

    def test_quick_add_widget_present(self):
        keys = [w["key"] for w in self.client.get(reverse("hub")).json()["widgets"]]
        self.assertIn("quick_add", keys)

    def test_notifications_summary_widget_shows_unread(self):
        from apps.notifications.services import create_notification
        create_notification(self.admin, title="Task approved", message="Nice work")
        resp = self.client.get(reverse("hub"))
        widget = next(w for w in resp.json()["widgets"] if w["key"] == "notifications_summary")
        self.assertEqual(widget["meta"]["unread_count"], 1)
        self.assertIn("Task approved", [n["title"] for n in widget["items"]])

    def test_notifications_summary_is_not_kiosk_safe(self):
        keys = [w["key"] for w in self.client.get(reverse("kiosk-hub")).json()["widgets"]]
        self.assertNotIn("notifications_summary", keys)


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

    def test_config_hides_widgets_for_node_user_cannot_open(self):
        from apps.nodes.services import enable_node

        enable_node(self.admin, "solace")
        _login(self.client, "parentuser")
        self.assertFalse(any(key.startswith("solace_") for key in self._config()))

    def test_config_includes_widgets_after_explicit_node_access(self):
        from apps.nodes.services import enable_node

        enable_node(self.admin, "solace")
        grant_user_permission(self.user, "solace.view")
        _login(self.client, "parentuser")
        self.assertTrue(any(key.startswith("solace_") for key in self._config()))

    def test_admin_can_configure_household_widget(self):
        _login(self.client, "admin")
        resp = self.client.patch(
            reverse("hub-widget-household", args=["atlas_todos"]),
            {"size": "large", "is_enabled": True},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._config()["atlas_todos"]["size"], "large")

    def test_admin_can_configure_countdown_widget(self):
        _login(self.client, "admin")
        resp = self.client.patch(
            reverse("hub-widget-household", args=["countdown"]),
            {
                "is_enabled": True,
                "size": "small",
                "settings": {"title": "Our holiday", "target_date": "2030-12-20", "target_time": "17:30"},
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        config = self._config()["countdown"]
        self.assertTrue(config["household_enabled"])
        self.assertEqual(config["settings"]["title"], "Our holiday")

        widget = next(
            item for item in self.client.get(reverse("hub")).json()["widgets"]
            if item["key"] == "countdown"
        )
        self.assertEqual(widget["meta"]["target_date"], "2030-12-20")
        self.assertEqual(widget["meta"]["target_time"], "17:30")
        self.assertIn("T17:30:00", widget["meta"]["target_at"])

    def test_countdown_defaults_missing_time_to_noon(self):
        _login(self.client, "admin")
        resp = self.client.patch(
            reverse("hub-widget-household", args=["countdown"]),
            {"settings": {"title": "Holiday", "target_date": "2030-12-20"}},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        widget = next(
            item for item in self.client.get(reverse("hub")).json()["widgets"]
            if item["key"] == "countdown"
        )
        self.assertEqual(widget["meta"]["target_time"], "12:00")
        self.assertIn("T12:00:00", widget["meta"]["target_at"])

    def test_countdown_rejects_invalid_target_date(self):
        _login(self.client, "admin")
        resp = self.client.patch(
            reverse("hub-widget-household", args=["countdown"]),
            {"settings": {"title": "Holiday", "target_date": "not-a-date"}},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

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

    def test_user_can_reorder_enabled_widgets_in_one_request(self):
        _login(self.client, "parentuser")
        before = [
            row["key"] for row in self.client.get(reverse("hub-widget-config")).json()["widgets"]
            if row["household_enabled"]
        ]
        desired = list(reversed(before))
        resp = self.client.patch(
            reverse("hub-widget-user-order"),
            {"keys": desired},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        actual = [
            row["key"] for row in resp.json()["widgets"]
            if row["household_enabled"]
        ]
        self.assertEqual(actual, desired)
        hub_keys = [row["key"] for row in self.client.get(reverse("hub")).json()["widgets"]]
        self.assertEqual(hub_keys, [key for key in desired if key in hub_keys])

    def test_bulk_reorder_requires_each_enabled_widget_once(self):
        _login(self.client, "parentuser")
        resp = self.client.patch(
            reverse("hub-widget-user-order"),
            {"keys": ["atlas_todos", "atlas_todos"]},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_unknown_widget_key_rejected(self):
        _login(self.client, "admin")
        resp = self.client.patch(
            reverse("hub-widget-household", args=["nope_widget"]),
            {"size": "small"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
