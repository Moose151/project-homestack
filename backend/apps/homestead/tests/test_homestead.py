"""Homestead tests — home/property hub V1. Permission tests first (D10).

Covers:
- Permissions across roles (unauthenticated/guest/user/child) on maintenance.
- CRUD for property, appliances, maintenance, providers, improvements.
- Calendar sync: maintenance next_due_at and improvement target_date create/delete a
  CalendarEvent via the scheduling helper (D7), tagged source_node = "homestead".
- Complete maintenance: stamps last_done_at and advances next_due_at by its RRULE (D8);
  non-recurring tasks have their reminder cleared.
- Visibility: a user's private appliance is hidden from another user and from children.
- Search + Hub widgets.
"""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.homestead.services import (
    complete_maintenance,
    create_appliance,
    create_improvement,
    create_maintenance,
    create_property,
    create_provider,
    create_household_cost,
    create_insurance_policy,
    delete_maintenance,
    update_improvement,
)
from apps.scheduling.models import CalendarEvent
from apps.solace.models import Bill


def _make_user(username, role=User.Role.ADMIN, is_child=False) -> User:
    user = User.objects.create_user(
        username=username, display_name=username.capitalize(), role=role, password="pass123!"
    )
    user.set_pin("1234")
    if is_child:
        user.is_child_account = True
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


def _future(hours=48):
    return timezone.now() + timezone.timedelta(hours=hours)


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

class HomesteadPermissionTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        self.user = _make_user("user", User.Role.USER)
        self.guest = _make_user("guest", User.Role.GUEST)
        self.child = _make_user("child", User.Role.USER, is_child=True)
        self.url = reverse("homestead-maintenance-list")

    def test_unauthenticated_rejected(self):
        self.assertIn(self.client.get(self.url).status_code, [401, 403])

    def test_guest_can_view(self):
        _login(self.client, "guest")
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_guest_cannot_create(self):
        _login(self.client, "guest")
        resp = self.client.post(self.url, {"title": "Bleed rads"}, content_type="application/json")
        self.assertIn(resp.status_code, [401, 403])

    def test_user_can_create(self):
        _login(self.client, "user")
        resp = self.client.post(self.url, {"title": "Clean gutters"}, content_type="application/json")
        self.assertEqual(resp.status_code, 201)

    def test_child_cannot_create(self):
        _login(self.client, "child")
        resp = self.client.post(self.url, {"title": "Paint"}, content_type="application/json")
        self.assertIn(resp.status_code, [401, 403])

    def test_user_cannot_delete(self):
        _login(self.client, "user")
        task = create_maintenance(self.admin, title="Service boiler")
        resp = self.client.delete(reverse("homestead-maintenance-detail", args=[task.id]))
        self.assertIn(resp.status_code, [401, 403])

    def test_admin_can_delete(self):
        _login(self.client, "admin")
        task = create_maintenance(self.admin, title="Service boiler")
        resp = self.client.delete(reverse("homestead-maintenance-detail", args=[task.id]))
        self.assertEqual(resp.status_code, 204)


class HomesteadFinancePermissionTests(TestCase):
    """Costs and policy data need Homestead + Solace permission and password re-auth."""

    def setUp(self):
        self.admin = _make_user("finance_admin", User.Role.ADMIN)
        self.manager = _make_user("finance_manager", User.Role.MANAGER)
        self.url = reverse("homestead-insurance-list")

    def test_unauthenticated_rejected(self):
        self.assertIn(self.client.get(self.url).status_code, [401, 403])

    def test_admin_requires_password_reauth(self):
        _login(self.client, "finance_admin")
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_admin_can_view_after_reauth(self):
        _login(self.client, "finance_admin")
        _reauth(self.client)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_manager_is_not_granted_solace_access_by_default(self):
        _login(self.client, "finance_manager")
        _reauth(self.client)
        self.assertIn(self.client.get(self.url).status_code, [401, 403])


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

class HomesteadCrudTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        _login(self.client, "admin")

    def test_property_crud(self):
        resp = self.client.post(
            reverse("homestead-property-list"),
            {"name": "Oak Cottage", "property_type": "house", "water_shutoff": "under sink"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        pid = resp.json()["id"]
        resp = self.client.patch(
            reverse("homestead-property-detail", args=[pid]),
            {"boiler_location": "Loft"}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["boiler_location"], "Loft")

    def test_appliance_crud(self):
        resp = self.client.post(
            reverse("homestead-appliance-list"),
            {"name": "Boiler", "category": "heating", "brand": "Worcester",
             "warranty_expires_at": "2030-01-01"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["brand"], "Worcester")

    def test_maintenance_requires_title(self):
        resp = self.client.post(
            reverse("homestead-maintenance-list"), {"title": ""}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_maintenance_links_appliance(self):
        appliance = create_appliance(self.admin, name="Boiler", category="heating")
        resp = self.client.post(
            reverse("homestead-maintenance-list"),
            {"title": "Annual boiler service", "appliance_id": appliance.id,
             "next_due_at": _future().isoformat(), "recurrence_rule": "FREQ=YEARLY"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["appliance_id"], appliance.id)

    def test_provider_crud(self):
        resp = self.client.post(
            reverse("homestead-provider-list"),
            {"name": "Bob's Plumbing", "trade": "plumber", "phone": "0123"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["trade"], "plumber")

    def test_improvement_crud(self):
        resp = self.client.post(
            reverse("homestead-improvement-list"),
            {"title": "Repaint living room", "status": "planned", "room": "Living room"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.json()["is_open"])


# ---------------------------------------------------------------------------
# Calendar sync (D7)
# ---------------------------------------------------------------------------

class HomesteadCalendarSyncTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)

    def test_maintenance_due_creates_event(self):
        t = create_maintenance(self.admin, title="Clean gutters", next_due_at=_future())
        t.refresh_from_db()
        self.assertIsNotNone(t.calendar_event_id)
        event = CalendarEvent.objects.get(pk=t.calendar_event_id)
        self.assertEqual(event.source_node.key, "homestead")
        self.assertIn("gutters", event.title.lower())

    def test_maintenance_without_due_creates_no_event(self):
        t = create_maintenance(self.admin, title="Someday task")
        self.assertIsNone(t.calendar_event_id)

    def test_deleting_maintenance_deletes_event(self):
        t = create_maintenance(self.admin, title="Service boiler", next_due_at=_future())
        event_id = t.calendar_event_id
        delete_maintenance(self.admin, t)
        self.assertFalse(CalendarEvent.objects.filter(pk=event_id).exists())

    def test_open_improvement_with_target_creates_event(self):
        imp = create_improvement(self.admin, title="New patio", status="planned", target_date=_future())
        imp.refresh_from_db()
        self.assertIsNotNone(imp.calendar_event_id)
        self.assertEqual(CalendarEvent.objects.get(pk=imp.calendar_event_id).source_node.key, "homestead")

    def test_completed_improvement_removes_event(self):
        imp = create_improvement(self.admin, title="New patio", status="planned", target_date=_future())
        self.assertIsNotNone(imp.calendar_event_id)
        update_improvement(self.admin, imp, status="done")
        imp.refresh_from_db()
        self.assertIsNone(imp.calendar_event_id)


# ---------------------------------------------------------------------------
# Complete maintenance (RRULE advance, D8)
# ---------------------------------------------------------------------------

class HomesteadCompleteMaintenanceTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)

    def test_recurring_task_advances_next_due(self):
        past_due = timezone.now() - timezone.timedelta(days=1)
        t = create_maintenance(
            self.admin, title="Bins out", next_due_at=past_due, recurrence_rule="FREQ=WEEKLY"
        )
        completed = complete_maintenance(self.admin, t)
        self.assertIsNotNone(completed.last_done_at)
        self.assertIsNotNone(completed.next_due_at)
        self.assertGreater(completed.next_due_at, timezone.now())

    def test_non_recurring_task_clears_reminder(self):
        t = create_maintenance(self.admin, title="Fix fence", next_due_at=_future())
        completed = complete_maintenance(self.admin, t)
        self.assertIsNotNone(completed.last_done_at)
        self.assertIsNone(completed.next_due_at)

    def test_complete_via_api(self):
        _login(self.client, "admin")
        t = create_maintenance(self.admin, title="Test smoke alarms", next_due_at=_future())
        resp = self.client.post(reverse("homestead-maintenance-complete", args=[t.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.json()["last_done_at"])


# ---------------------------------------------------------------------------
# Visibility (D10)
# ---------------------------------------------------------------------------

class HomesteadVisibilityTests(TestCase):
    def setUp(self):
        self.owner = _make_user("owner", User.Role.USER)
        self.other = _make_user("other", User.Role.USER)
        self.child = _make_user("child", User.Role.USER, is_child=True)
        create_appliance(self.owner, name="Safe", category="security", visibility="private")

    def test_owner_sees_own_private_appliance(self):
        from apps.homestead.selectors import list_appliances
        self.assertIn("Safe", [a.name for a in list_appliances(self.owner)])

    def test_other_user_cannot_see_private_appliance(self):
        from apps.homestead.selectors import list_appliances
        self.assertNotIn("Safe", [a.name for a in list_appliances(self.other)])

    def test_child_cannot_see_private_appliance(self):
        from apps.homestead.selectors import list_appliances
        self.assertNotIn("Safe", [a.name for a in list_appliances(self.child)])

    def test_private_detail_cannot_be_edited_by_another_user(self):
        appliance = create_appliance(
            self.owner, name="Alarm code", category="security", visibility="private"
        )
        _login(self.client, "other")
        resp = self.client.patch(
            reverse("homestead-appliance-detail", args=[appliance.id]),
            {"name": "Changed"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# Costs & cover → Solace bridge (D4)
# ---------------------------------------------------------------------------

class HomesteadFinanceSyncTests(TestCase):
    def setUp(self):
        self.admin = _make_user("home_finance_admin", User.Role.ADMIN)
        _login(self.client, "home_finance_admin")
        _reauth(self.client)

    def test_insurance_policy_crud_syncs_linked_solace_bill(self):
        renewal = _future().isoformat()
        resp = self.client.post(
            reverse("homestead-insurance-list"),
            {
                "name": "Home and contents",
                "policy_type": "building_contents",
                "provider": "Cover Co",
                "policy_number": "POL-123",
                "premium_amount": "1450.25",
                "billing_cycle": "yearly",
                "next_renewal_at": renewal,
                "standard_excess": "750.00",
                "additional_excesses": "Flood: $1,500",
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        policy_id = resp.json()["id"]
        bill = Bill.objects.get(
            source_node="homestead",
            source_record_type="insurance_policy",
            source_record_id=policy_id,
        )
        self.assertEqual(str(bill.amount), "1450.25")
        self.assertEqual(bill.category, "insurance")
        self.assertEqual(bill.recurrence_rule, "FREQ=YEARLY")
        self.assertEqual(resp.json()["solace_bill_ref"], bill.id)

        resp = self.client.patch(
            reverse("homestead-insurance-detail", args=[policy_id]),
            {"premium_amount": "1525.00"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        bill.refresh_from_db()
        self.assertEqual(str(bill.amount), "1525.00")

        resp = self.client.patch(
            reverse("homestead-insurance-detail", args=[policy_id]),
            {"is_active": False},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.json()["solace_bill_ref"])
        self.assertFalse(Bill.objects.filter(pk=bill.id).exists())

        resp = self.client.patch(
            reverse("homestead-insurance-detail", args=[policy_id]),
            {"is_active": True},
            content_type="application/json",
        )
        self.assertEqual(resp.json()["solace_bill_ref"], bill.id)
        self.assertTrue(Bill.objects.filter(pk=bill.id).exists())

        resp = self.client.delete(reverse("homestead-insurance-detail", args=[policy_id]))
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Bill.objects.filter(pk=bill.id).exists())

    def test_rates_water_and_gas_map_to_solace_categories(self):
        cases = [
            ("rates", "Council rates", "council"),
            ("water", "Water", "utilities"),
            ("gas", "Gas", "utilities"),
        ]
        for cost_type, name, expected_category in cases:
            with self.subTest(cost_type=cost_type):
                cost = create_household_cost(
                    self.admin,
                    name=name,
                    cost_type=cost_type,
                    amount="240.00",
                    billing_cycle="quarterly",
                    next_due_at=_future(),
                )
                bill = Bill.objects.get(
                    source_node="homestead",
                    source_record_type="household_cost",
                    source_record_id=cost.id,
                )
                self.assertEqual(bill.category, expected_category)
                self.assertEqual(bill.recurrence_rule, "FREQ=MONTHLY;INTERVAL=3")
                self.assertEqual(cost.solace_bill_ref, bill.id)

    def test_policy_service_creates_financial_calendar_event_only_in_solace(self):
        policy = create_insurance_policy(
            self.admin,
            name="Building insurance",
            premium_amount="900.00",
            next_renewal_at=_future(),
            billing_cycle="yearly",
        )
        bill = Bill.objects.get(pk=policy.solace_bill_ref)
        event = CalendarEvent.objects.get(pk=bill.calendar_event_id)
        self.assertEqual(event.source_node.key, "solace")
        self.assertEqual(event.sensitivity, "financial")


# ---------------------------------------------------------------------------
# Search + Hub widgets
# ---------------------------------------------------------------------------

class HomesteadSearchAndHubTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        _login(self.client, "admin")

    def test_search_matches_appliances_and_improvements(self):
        create_appliance(self.admin, name="Dishwasher", brand="Bosch")
        create_improvement(self.admin, title="Loft conversion", status="idea")
        resp = self.client.get(reverse("homestead-search"), {"q": "Bosch"})
        self.assertEqual([a["name"] for a in resp.json()["appliances"]], ["Dishwasher"])
        resp = self.client.get(reverse("homestead-search"), {"q": "Loft"})
        self.assertEqual([i["title"] for i in resp.json()["improvements"]], ["Loft conversion"])

    def test_maintenance_widget_lists_due(self):
        from apps.hub.services import _homestead_widget_content
        create_maintenance(self.admin, title="Service boiler", next_due_at=_future())
        create_maintenance(self.admin, title="Someday")  # no due date → excluded
        content = _homestead_widget_content("homestead_maintenance", self.admin)
        self.assertEqual([t["title"] for t in content], ["Service boiler"])

    def test_warranties_widget_lists_expiring(self):
        from apps.hub.services import _homestead_widget_content
        soon = (timezone.now() + timezone.timedelta(days=20)).date().isoformat()
        far = (timezone.now() + timezone.timedelta(days=400)).date().isoformat()
        create_appliance(self.admin, name="Washer", warranty_expires_at=soon)
        create_appliance(self.admin, name="Fridge", warranty_expires_at=far)
        content = _homestead_widget_content("homestead_warranties", self.admin)
        self.assertEqual([a["name"] for a in content], ["Washer"])

    def test_improvements_widget_lists_open(self):
        from apps.hub.services import _homestead_widget_content
        create_improvement(self.admin, title="Kitchen redo", status="in_progress")
        create_improvement(self.admin, title="Old job", status="done")
        content = _homestead_widget_content("homestead_improvements", self.admin)
        self.assertEqual([i["title"] for i in content], ["Kitchen redo"])
