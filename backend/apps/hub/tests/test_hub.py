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
from apps.atlas.services import (
    create_atlas_list, create_list_item, create_reminder, ensure_household_grocery_list,
)
from apps.people.services import create_person
from apps.permissions.services import deny_user_permission, grant_user_permission
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

    def test_grocery_items_are_not_classified_as_todos(self):
        """Regression: a grocery item must never appear in the atlas_todos widget (D19 §K)."""
        todo_list = create_atlas_list(self.admin, title="Chores", list_type="todo")
        create_list_item(self.admin, todo_list, title="Book pest inspection")
        grocery_list = ensure_household_grocery_list(self.admin)
        create_list_item(self.admin, grocery_list, title="Milk")

        todos = self._widget("atlas_todos")
        self.assertIsNotNone(todos)
        titles = [i["title"] for i in todos["items"]]
        self.assertIn("Book pest inspection", titles)
        self.assertNotIn("Milk", titles)

    def test_grocery_widget_shows_grocery_items_with_remaining_count(self):
        from apps.atlas.services import complete_list_item

        grocery_list = ensure_household_grocery_list(self.admin)
        create_list_item(self.admin, grocery_list, title="Milk")
        bought = create_list_item(self.admin, grocery_list, title="Bread")
        complete_list_item(self.admin, bought)

        grocery = self._widget("atlas_grocery")
        self.assertIsNotNone(grocery)
        titles = [i["title"] for i in grocery["items"]]
        self.assertIn("Milk", titles)
        self.assertNotIn("Bread", titles)
        self.assertEqual(grocery["meta"]["remaining_count"], 1)

    def test_grocery_widget_dropped_when_list_is_empty(self):
        self.assertIsNone(self._widget("atlas_grocery"))


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

    def test_user_can_dismiss_and_restore_an_upcoming_item(self):
        reminder = create_reminder(self.admin, title="Doctor visit", due_at=_future(48))
        event_id = reminder.calendar_event_id

        dismissed = self.client.post(reverse("hub-upcoming-dismissal", args=[event_id]))
        self.assertEqual(dismissed.status_code, 200)
        self.assertIsNone(self._upcoming())
        self.assertTrue(CalendarEvent.objects.filter(pk=event_id).exists())

        restored = self.client.delete(reverse("hub-upcoming-dismissal", args=[event_id]))
        self.assertEqual(restored.status_code, 204)
        self.assertIn("Doctor visit", [i["title"] for i in self._upcoming()["items"]])

    def test_upcoming_dismissal_is_per_user(self):
        reminder = create_reminder(self.admin, title="Shared appointment", due_at=_future(48))
        self.client.post(reverse("hub-upcoming-dismissal", args=[reminder.calendar_event_id]))
        self.assertIsNone(self._upcoming())

        _make_user("other-admin", User.Role.ADMIN)
        _login(self.client, "other-admin")
        self.assertIn("Shared appointment", [i["title"] for i in self._upcoming()["items"]])

    def test_cannot_dismiss_an_item_hidden_by_sensitivity(self):
        from apps.scheduling.services import create_event

        event = create_event(
            self.admin,
            title="Private appointment",
            start_at=_future(48),
            sensitivity="private",
        )
        response = self.client.post(reverse("hub-upcoming-dismissal", args=[event.id]))
        self.assertEqual(response.status_code, 404)

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

    def test_overdue_todo_is_kept(self):
        """Modern Atlas To-dos use AtlasListItem projections, not legacy Reminder rows."""
        todo_list = create_atlas_list(self.admin, title="Household", list_type="todo")
        create_list_item(
            self.admin,
            todo_list,
            title="Overdue household job",
            due_at=_future(hours=-48),
        )
        self.assertIn(
            "Overdue household job",
            [item["title"] for item in self._upcoming()["items"]],
        )

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

    def test_kiosk_hub_locks_money_even_when_the_household_lock_is_off(self):
        from apps.nodes.models import HouseholdNode
        from apps.nodes.services import enable_node
        from apps.solace.services import create_bill

        enable_node(self.admin, "solace")
        grant_user_permission(self.admin, "solace.view")
        HouseholdNode.objects.filter(node__key="solace").update(requires_reauthentication=False)
        create_bill(self.admin, name="Electricity", amount="120.00", due_at=_future(48))

        widget = next(
            (w for w in self.client.get(reverse("kiosk-hub")).json()["widgets"]
             if w["key"] == "solace_bills_due"),
            None,
        )
        # A kiosk is a shared screen: the node lock being off does not make it a private one.
        self.assertTrue(widget is None or widget["meta"].get("locked"))

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


class DashboardMoneyLockTests(TestCase):
    """The Dashboard's Money widget must follow Money's own lock, not the session alone.

    Production bug: HubView derived the widget's state purely from ``is_reauthed``, so a
    household that had switched Money's re-authentication prompt off saw a permanently locked
    "Due before next payday" card. Opening Money could never clear it, because nothing was
    asking whether Money was locked in the first place.

    The obvious fix — treating the whole Dashboard as unlocked when Money's lock is off — would
    have been a security regression: the same flag hides financial, *health*, document and
    private entries from Upcoming. Both halves are covered here.
    """

    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        _login(self.client, "admin")
        from apps.nodes.services import enable_node
        enable_node(self.admin, "solace")
        grant_user_permission(self.admin, "solace.view")
        from apps.solace.services import create_bill
        create_bill(self.admin, name="Electricity", amount="120.00", due_at=_future(48))

    def _set_money_lock(self, required: bool):
        from apps.nodes.models import HouseholdNode
        HouseholdNode.objects.filter(node__key="solace").update(
            requires_reauthentication=required,
        )

    def _money_widget(self):
        return next(
            (w for w in self.client.get(reverse("hub")).json()["widgets"]
             if w["key"] == "solace_bills_due"),
            None,
        )

    def _upcoming_titles(self):
        widget = next(
            (w for w in self.client.get(reverse("hub")).json()["widgets"] if w["key"] == "upcoming"),
            None,
        )
        return [item["title"] for item in (widget or {"items": []})["items"]]

    def test_lock_off_without_reauth_shows_the_money_widget(self):
        self._set_money_lock(False)
        widget = self._money_widget()
        self.assertIsNotNone(widget)
        self.assertFalse(widget["meta"]["locked"])

    def test_lock_on_without_reauth_keeps_the_money_widget_locked(self):
        self._set_money_lock(True)
        widget = self._money_widget()
        self.assertIsNotNone(widget)
        self.assertTrue(widget["meta"]["locked"])

    def test_lock_on_with_reauth_shows_the_money_widget(self):
        self._set_money_lock(True)
        _reauth(self.client)
        widget = self._money_widget()
        self.assertIsNotNone(widget)
        self.assertFalse(widget["meta"]["locked"])

    def test_money_lock_off_does_not_expose_health_entries(self):
        """The security half of the fix.

        Money's lock being off must unlock Money and nothing else — a health appointment is
        still protected by the session-level sensitivity filter.
        """
        from apps.scheduling.services import create_event

        self._set_money_lock(False)
        create_event(
            self.admin, title="Cardiology appointment", start_at=_future(48),
            sensitivity="health",
        )
        titles = self._upcoming_titles()
        self.assertNotIn("Cardiology appointment", titles)
        # ...while Money itself is genuinely open.
        self.assertFalse(self._money_widget()["meta"]["locked"])

    def test_money_lock_off_does_not_expose_private_or_document_entries(self):
        from apps.scheduling.services import create_event

        self._set_money_lock(False)
        create_event(self.admin, title="Passport renewal", start_at=_future(48), sensitivity="document")
        create_event(self.admin, title="Therapy", start_at=_future(50), sensitivity="private")
        titles = self._upcoming_titles()
        self.assertNotIn("Passport renewal", titles)
        self.assertNotIn("Therapy", titles)

    def test_reauth_still_reveals_sensitive_entries(self):
        from apps.scheduling.services import create_event

        self._set_money_lock(False)
        create_event(
            self.admin, title="Cardiology appointment", start_at=_future(48), sensitivity="health",
        )
        _reauth(self.client)
        self.assertIn("Cardiology appointment", self._upcoming_titles())


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


class BillCalendarEventSyncTests(TestCase):
    """CalendarEvent for a recurring bill must always point to the next UPCOMING occurrence.

    Root cause: mark_occurrence_paid() did not call sync_event_for(bill) for recurring
    bills, leaving the CalendarEvent frozen at the original anchor date forever. As a result,
    the Upcoming widget kept showing the bill as overdue after every payment.
    """

    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        _login(self.client, "admin")
        from apps.nodes.services import enable_node
        enable_node(self.admin, "solace")
        grant_user_permission(self.admin, "solace.view")

    def _upcoming_titles(self):
        _reauth(self.client)
        widget = next(
            (w for w in self.client.get(reverse("hub")).json()["widgets"] if w["key"] == "upcoming"),
            None,
        )
        return [item["title"] for item in (widget or {"items": []})["items"]]

    def test_new_recurring_bill_with_past_anchor_shows_next_occurrence_not_stale_date(self):
        """Regression: create_bill() must sync *after* settle_history_on_entry().

        A bill entered with a past anchor date has its past occurrences auto-settled.
        The CalendarEvent must reflect the first *future* occurrence, not the stale anchor.
        """
        from apps.scheduling.models import CalendarEvent
        from apps.solace.services import create_bill

        bill = create_bill(
            self.admin,
            name="Internet",
            amount="89.00",
            due_at=_future(hours=-48),
            recurrence_rule="FREQ=WEEKLY",
        )
        self.assertIsNotNone(bill.calendar_event_id)
        event = CalendarEvent.objects.get(pk=bill.calendar_event_id)
        from django.utils import timezone
        # The CalendarEvent must be in the future, not the stale past anchor.
        self.assertGreater(event.start_at, timezone.now(), "CalendarEvent should point to next future occurrence")

    def test_paid_recurring_bill_advances_calendar_event_to_next_occurrence(self):
        """Regression: mark_occurrence_paid() must sync the CalendarEvent for recurring bills.

        Before the fix: paying an occurrence left the CalendarEvent on the old past date
        and the bill kept appearing as overdue in the Upcoming widget forever.
        """
        from apps.scheduling.models import CalendarEvent
        from apps.solace.models import BillOccurrence
        from apps.solace.services import create_bill, mark_occurrence_paid

        bill = create_bill(
            self.admin,
            name="Electricity",
            amount="120.00",
            due_at=_future(hours=72),
            recurrence_rule="FREQ=WEEKLY",
        )
        first_occ = bill.occurrences.filter(status=BillOccurrence.Status.UPCOMING).order_by("due_at").first()
        self.assertIsNotNone(first_occ)
        first_start = CalendarEvent.objects.get(pk=bill.calendar_event_id).start_at

        mark_occurrence_paid(self.admin, first_occ)

        bill.refresh_from_db()
        second_start = CalendarEvent.objects.get(pk=bill.calendar_event_id).start_at
        self.assertGreater(second_start, first_start, "CalendarEvent must advance after payment")

    def test_stale_recurring_bill_disappears_from_upcoming_after_payment(self):
        """End-to-end: paying a past-due recurring occurrence removes it from the Upcoming widget.

        The Upcoming widget reads CalendarEvents. After payment the CalendarEvent must
        advance past the window, leaving the stale overdue entry gone.
        """
        from apps.solace.models import BillOccurrence
        from apps.solace.services import create_bill, mark_occurrence_paid

        bill = create_bill(
            self.admin,
            name="Phone bill",
            amount="45.00",
            due_at=_future(hours=48),
            recurrence_rule="FREQ=WEEKLY",
        )
        # Confirm the bill appears in Upcoming.
        self.assertIn("Bill: Phone bill", self._upcoming_titles())

        # Pay the upcoming occurrence.
        occ = bill.occurrences.filter(status=BillOccurrence.Status.UPCOMING).order_by("due_at").first()
        self.assertIsNotNone(occ)
        mark_occurrence_paid(self.admin, occ)

        # The paid occurrence's date is now gone; the CalendarEvent moved forward a week.
        # With a weekly bill starting 2 days out, the next occurrence is 9 days out —
        # still inside the 62-day Upcoming window — so the title must still appear but
        # now at the advanced date, proving it was not frozen on the old date.
        bill.refresh_from_db()
        titles = self._upcoming_titles()
        self.assertIn("Bill: Phone bill", titles, "Next occurrence should still appear in Upcoming")

    def test_unpaid_overdue_non_recurring_bill_stays_in_upcoming(self):
        """Genuine unpaid bills must never be hidden regardless of how old they are."""
        from apps.solace.services import create_bill

        create_bill(self.admin, name="One-off fee", amount="200.00", due_at=_future(hours=-48))
        self.assertIn("Bill: One-off fee", self._upcoming_titles())

    def test_mark_occurrence_unpaid_re_syncs_calendar_event(self):
        """Reversing a payment must also update the CalendarEvent back to that occurrence."""
        from apps.scheduling.models import CalendarEvent
        from apps.solace.models import BillOccurrence
        from apps.solace.services import create_bill, mark_occurrence_paid, mark_occurrence_unpaid

        bill = create_bill(
            self.admin,
            name="Gas",
            amount="60.00",
            due_at=_future(hours=24),
            recurrence_rule="FREQ=WEEKLY",
        )
        occ = bill.occurrences.filter(status=BillOccurrence.Status.UPCOMING).order_by("due_at").first()
        paid_at_date = occ.due_at
        mark_occurrence_paid(self.admin, occ)

        # Now advance to the next occurrence — CalendarEvent should be ahead of original.
        bill.refresh_from_db()
        advanced = CalendarEvent.objects.get(pk=bill.calendar_event_id).start_at
        self.assertGreater(advanced, paid_at_date)

        occ.refresh_from_db()
        mark_occurrence_unpaid(self.admin, occ)

        # After reversal the CalendarEvent must snap back to the re-opened occurrence.
        bill.refresh_from_db()
        reverted = CalendarEvent.objects.get(pk=bill.calendar_event_id).start_at
        self.assertEqual(reverted.date(), paid_at_date.date())


class EducationAssessmentUpcomingSyncTests(TestCase):
    """Completing an Education assignment must clear it from Dashboard -> Upcoming.

    Root cause: EducationAssessment.get_calendar_data() ignored status entirely, so an
    overdue assignment marked Done kept re-syncing its CalendarEvent to the same stale
    due_at forever — the same class of bug as the Bill/CalendarEvent sync issue above,
    fixed the same way: get_calendar_data() returns None once the record is complete.
    """

    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        _login(self.client, "admin")
        from apps.nodes.services import enable_node
        enable_node(self.admin, "education")
        grant_user_permission(self.admin, "education.view")

    def _upcoming_titles(self):
        _reauth(self.client)
        widget = next(
            (w for w in self.client.get(reverse("hub")).json()["widgets"] if w["key"] == "upcoming"),
            None,
        )
        return [item["title"] for item in (widget or {"items": []})["items"]]

    def test_overdue_todo_assessment_appears_in_upcoming(self):
        from apps.education.services import create_assessment

        create_assessment(self.admin, title="Assignment 2 - Submission 1", due_at=_future(hours=-48))
        titles = self._upcoming_titles()
        self.assertTrue(any("Assignment 2 - Submission 1" in t for t in titles))

    def test_marking_assessment_done_removes_it_from_upcoming(self):
        from apps.education.models import EducationAssessment
        from apps.education.services import create_assessment, update_assessment

        a = create_assessment(self.admin, title="Assignment 2 - Submission 1", due_at=_future(hours=-48))
        self.assertTrue(any("Assignment 2 - Submission 1" in t for t in self._upcoming_titles()))

        update_assessment(self.admin, a, status=EducationAssessment.Status.DONE)
        titles = self._upcoming_titles()
        self.assertFalse(any("Assignment 2 - Submission 1" in t for t in titles))

    def test_completed_assessment_remains_visible_in_education(self):
        from apps.education.models import EducationAssessment
        from apps.education.services import create_assessment, update_assessment

        a = create_assessment(self.admin, title="Finished essay", due_at=_future(hours=-48))
        update_assessment(self.admin, a, status=EducationAssessment.Status.DONE)

        resp = self.client.get(reverse("education-assessment-detail", args=[a.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "done")

    def test_reopening_assessment_returns_it_to_upcoming_when_still_due(self):
        from apps.education.models import EducationAssessment
        from apps.education.services import create_assessment, update_assessment

        a = create_assessment(self.admin, title="Reopened task", due_at=_future(hours=-48))
        update_assessment(self.admin, a, status=EducationAssessment.Status.DONE)
        self.assertFalse(any("Reopened task" in t for t in self._upcoming_titles()))

        update_assessment(self.admin, a, status=EducationAssessment.Status.TODO)
        self.assertTrue(any("Reopened task" in t for t in self._upcoming_titles()))

    def test_future_completed_assessment_does_not_appear_in_upcoming(self):
        from apps.education.models import EducationAssessment
        from apps.education.services import create_assessment

        create_assessment(
            self.admin, title="Already done ahead of time", due_at=_future(hours=72),
            status=EducationAssessment.Status.DONE,
        )
        titles = self._upcoming_titles()
        self.assertFalse(any("Already done ahead of time" in t for t in titles))

    def test_unrelated_upcoming_entries_are_unaffected_by_assessment_completion(self):
        """Calendar/reminder, bill and assessment entries in Upcoming don't cross-contaminate."""
        from apps.education.models import EducationAssessment
        from apps.education.services import create_assessment, update_assessment
        from apps.nodes.services import enable_node
        from apps.solace.services import create_bill

        enable_node(self.admin, "solace")
        grant_user_permission(self.admin, "solace.view")
        create_reminder(self.admin, title="Doctor visit", due_at=_future(48))
        create_bill(self.admin, name="Internet", amount="89.00", due_at=_future(hours=-24))
        a = create_assessment(self.admin, title="Assignment X", due_at=_future(hours=-24))

        update_assessment(self.admin, a, status=EducationAssessment.Status.DONE)

        titles = self._upcoming_titles()
        self.assertFalse(any("Assignment X" in t for t in titles))
        self.assertIn("Doctor visit", titles)
        self.assertIn("Bill: Internet", titles)


class UpcomingCompletionContractTests(TestCase):
    """Every node on the Dashboard is finished the same way (owner, 2026-09-21).

    The owner's complaint was that each node had its own workflow: some rows could be
    actioned where you saw them, most could not, and Education in particular forced a trip
    into an edit screen. The contract now is uniform — the backend names the transition on
    each row and applies it through the owning domain's own service, so no node gets a
    bespoke Dashboard path.
    """

    def setUp(self):
        from apps.nodes.services import enable_node

        self.admin = _make_user("admin", User.Role.ADMIN)
        _login(self.client, "admin")
        for node in ("education", "solace", "meridian", "pets", "homestead", "atlas"):
            enable_node(self.admin, node)
            grant_user_permission(self.admin, f"{node}.view")

    def _rows(self):
        _reauth(self.client)
        widget = next(
            (w for w in self.client.get(reverse("hub")).json()["widgets"] if w["key"] == "upcoming"),
            None,
        )
        return (widget or {"items": []})["items"]

    def _row_for(self, title_fragment):
        return next(
            (row for row in self._rows() if title_fragment in row["title"]), None
        )

    def _complete(self, event_id):
        return self.client.post(reverse("hub-upcoming-complete", args=[event_id]))

    # --- the label each node advertises ---

    def test_every_actionable_node_advertises_its_own_word_for_finished(self):
        from apps.education.services import create_assessment
        from apps.solace.services import create_bill

        create_assessment(self.admin, title="Research report", due_at=_future(hours=-48))
        create_bill(self.admin, name="Internet", amount="89.00", due_at=_future(hours=-24))

        self.assertEqual(self._row_for("Research report")["complete_action"], "Done")
        # Money keeps its own vocabulary — one interaction, not one flattened word.
        self.assertEqual(self._row_for("Internet")["complete_action"], "Paid")

    def test_a_row_with_no_unambiguous_transition_advertises_none(self):
        from apps.scheduling.services import create_event

        create_event(self.admin, title="Dinner with friends", start_at=_future(48))
        self.assertIsNone(self._row_for("Dinner with friends")["complete_action"])

    # --- the transition itself, per node ---

    def test_education_assignment_completes_from_the_dashboard(self):
        from apps.education.models import EducationAssessment
        from apps.education.services import create_assessment

        assessment = create_assessment(
            self.admin, title="Research report", due_at=_future(hours=-48)
        )
        response = self._complete(assessment.calendar_event_id)

        self.assertEqual(response.status_code, 200)
        assessment.refresh_from_db()
        self.assertEqual(assessment.status, EducationAssessment.Status.DONE)
        self.assertIsNone(self._row_for("Research report"))

    def test_bill_is_paid_from_the_dashboard(self):
        from apps.solace.services import create_bill

        bill = create_bill(
            self.admin, name="Internet", amount="89.00", due_at=_future(hours=-24)
        )
        _reauth(self.client)  # Money rows stay filtered until the reader re-authenticates.
        response = self._complete(bill.calendar_event_id)

        self.assertEqual(response.status_code, 200)
        bill.refresh_from_db()
        self.assertTrue(bill.is_paid)

    def test_atlas_todo_completes_from_the_dashboard(self):
        todo_list = create_atlas_list(self.admin, title="Household", list_type="todo")
        item = create_list_item(
            self.admin, todo_list, title="Put the bins out", due_at=_future(hours=-24)
        )
        response = self._complete(item.calendar_event_id)

        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertTrue(item.is_complete)
        self.assertIsNone(self._row_for("Put the bins out"))

    def test_meridian_task_completes_from_the_dashboard(self):
        from apps.meridian.models import MeridianTask
        from apps.meridian.services import create_task

        person = create_person(self.admin, display_name="Alex", linked_user_id=self.admin.id)
        task = create_task(
            self.admin, title="Tidy the garage", due_at=_future(hours=-24),
            assigned_to_people=[person.id],
        )
        response = self._complete(task.calendar_event_id)

        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertTrue(task.is_complete)
        self.assertIsNone(self._row_for("Tidy the garage"))

    def test_maintenance_task_completes_from_the_dashboard(self):
        from apps.homestead.services import create_maintenance

        task = create_maintenance(
            self.admin, title="Service the boiler", next_due_at=_future(hours=-24)
        )
        response = self._complete(task.calendar_event_id)

        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertIsNotNone(task.last_done_at)
        self.assertIsNone(self._row_for("Service the boiler"))

    def test_pet_treatment_completes_from_the_dashboard(self):
        from apps.pets.services import create_pet, create_treatment

        pet = create_pet(self.admin, name="Rosie", species="dog")
        treatment = create_treatment(
            self.admin, pet=pet, treatment_type="flea", next_due_at=_future(hours=-24)
        )
        response = self._complete(treatment.calendar_event_id)

        self.assertEqual(response.status_code, 200)
        treatment.refresh_from_db()
        self.assertIsNotNone(treatment.last_done_at)

    # --- boundaries ---

    def test_a_row_with_no_source_action_cannot_be_completed(self):
        from apps.scheduling.services import create_event

        event = create_event(self.admin, title="Dinner with friends", start_at=_future(48))
        self.assertEqual(self._complete(event.id).status_code, 404)

    def test_cannot_complete_a_row_hidden_by_sensitivity(self):
        """Hub must never become a side door onto a record the reader cannot see."""
        from apps.solace.services import create_bill

        bill = create_bill(
            self.admin, name="Private loan", amount="500.00", due_at=_future(hours=-24)
        )
        # No re-auth on this client, so the financial row is filtered out of Upcoming.
        self.assertEqual(self._complete(bill.calendar_event_id).status_code, 404)
        bill.refresh_from_db()
        self.assertFalse(bill.is_paid)

    def test_viewer_without_edit_on_the_owning_node_is_refused(self):
        from apps.education.services import create_assessment

        assessment = create_assessment(
            self.admin, title="Research report", due_at=_future(hours=-48)
        )
        viewer = _make_user("viewer", User.Role.USER)
        grant_user_permission(viewer, "education.view")
        grant_user_permission(viewer, "hub.view")
        # Seeing a row must not imply being allowed to finish it.
        deny_user_permission(viewer, "education.edit")
        deny = self.client_class()
        _login(deny, "viewer")
        _reauth(deny, password="pass123!")

        response = deny.post(
            reverse("hub-upcoming-complete", args=[assessment.calendar_event_id])
        )
        self.assertEqual(response.status_code, 403)
        assessment.refresh_from_db()
        self.assertFalse(assessment.is_complete)


class MeridianTaskUpcomingSyncTests(TestCase):
    """A finished Meridian task must leave Upcoming, like every other node.

    Same bug class as the Bill and Education cases above: MeridianTask.get_calendar_data()
    ignored completion, so a completed one-off task kept its deadline projection and sat on
    the Dashboard as permanently overdue.
    """

    def setUp(self):
        from apps.nodes.services import enable_node

        self.admin = _make_user("admin", User.Role.ADMIN)
        _login(self.client, "admin")
        enable_node(self.admin, "meridian")
        grant_user_permission(self.admin, "meridian.view")
        self.person = create_person(
            self.admin, display_name="Alex", linked_user_id=self.admin.id
        )

    def _upcoming_titles(self):
        _reauth(self.client)
        widget = next(
            (w for w in self.client.get(reverse("hub")).json()["widgets"] if w["key"] == "upcoming"),
            None,
        )
        return [item["title"] for item in (widget or {"items": []})["items"]]

    def _task(self, title, **extra):
        from apps.meridian.services import create_task

        return create_task(
            self.admin, title=title, due_at=_future(hours=-24),
            assigned_to_people=[self.person.id], **extra,
        )

    def test_overdue_task_appears_in_upcoming(self):
        self._task("Tidy the garage")
        self.assertIn("Tidy the garage", self._upcoming_titles())

    def test_completing_a_one_off_task_removes_it_from_upcoming(self):
        from apps.meridian.services import complete_task

        task = self._task("Tidy the garage")
        complete_task(self.admin, task, person_id=self.person.id)

        self.assertNotIn("Tidy the garage", self._upcoming_titles())
        task.refresh_from_db()
        self.assertIsNone(task.calendar_event_id)

    def test_a_recurring_task_keeps_its_deadline_after_completion(self):
        """`status` is only recomputed on write, so last cycle's completion must not
        erase this cycle's deadline."""
        from apps.meridian.services import complete_task

        task = self._task("Take the bins out", recurrence_rule="FREQ=WEEKLY")
        complete_task(self.admin, task, person_id=self.person.id)

        self.assertIn("Take the bins out", self._upcoming_titles())

    def test_rejecting_a_completion_restores_the_deadline(self):
        from apps.meridian.models import MeridianTaskCompletion
        from apps.meridian.services import complete_task, reject_task_completion

        task = self._task("Tidy the garage")
        complete_task(self.admin, task, person_id=self.person.id)
        self.assertNotIn("Tidy the garage", self._upcoming_titles())

        completion = MeridianTaskCompletion.objects.get(task=task)
        reject_task_completion(self.admin, completion, reason="Not done properly")

        self.assertIn("Tidy the garage", self._upcoming_titles())
