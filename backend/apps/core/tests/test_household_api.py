"""
Household endpoint tests — Phase 1.6, written FIRST per D10.

GET /api/v1/household/ — everyone with household.view
PATCH /api/v1/household/ — admin only (household.edit)
"""
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User


def _make_user(username, role=User.Role.USER, pin="1234") -> User:
    user = User.objects.create_user(
        username=username, display_name=username.title(),
        password="pass!", role=role,
    )
    user.set_pin(pin)
    user.save()
    return user


def _login(client, username, pin="1234"):
    client.post(reverse("auth-pin-login"), {"username": username, "pin": pin},
                content_type="application/json")


class HouseholdGetTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", role=User.Role.ADMIN)
        self.user = _make_user("user")
        self.url = reverse("household")

    def test_unauthenticated_denied(self):
        resp = self.client.get(self.url)
        self.assertIn(resp.status_code, [401, 403])

    def test_admin_can_get(self):
        _login(self.client, "admin")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("name", data)
        self.assertIn("timezone", data)
        self.assertIn("slug", data)

    def test_user_can_get(self):
        _login(self.client, "user")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)


class HouseholdPatchTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin2", role=User.Role.ADMIN)
        self.manager = _make_user("manager2", role=User.Role.MANAGER)
        self.user = _make_user("user2")
        self.url = reverse("household")

    def test_unauthenticated_cannot_patch(self):
        resp = self.client.patch(self.url, {"name": "X"}, content_type="application/json")
        self.assertIn(resp.status_code, [401, 403])

    def test_admin_can_patch_name(self):
        _login(self.client, "admin2")
        resp = self.client.patch(self.url, {"name": "Updated Name"},
                                 content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["name"], "Updated Name")

    def test_admin_can_patch_timezone(self):
        _login(self.client, "admin2")
        resp = self.client.patch(self.url, {"timezone": "Europe/London"},
                                 content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["timezone"], "Europe/London")

    def test_admin_can_set_calendar_defaults(self):
        _login(self.client, "admin2")
        resp = self.client.patch(
            self.url,
            {"calendar_default_view": "week", "calendar_week_start": 0, "calendar_time_format": "24h"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["calendar_default_view"], "week")
        self.assertEqual(data["calendar_week_start"], 0)
        self.assertEqual(data["calendar_time_format"], "24h")

    def test_calendar_defaults_exposed_on_get(self):
        _login(self.client, "admin2")
        data = self.client.get(self.url).json()
        self.assertIn("calendar_default_view", data)
        self.assertIn("calendar_week_start", data)
        self.assertIn("calendar_time_format", data)

    def test_manager_cannot_patch(self):
        _login(self.client, "manager2")
        resp = self.client.patch(self.url, {"name": "Hack"}, content_type="application/json")
        self.assertEqual(resp.status_code, 403)

    def test_user_cannot_patch(self):
        _login(self.client, "user2")
        resp = self.client.patch(self.url, {"name": "Hack"}, content_type="application/json")
        self.assertEqual(resp.status_code, 403)


class HouseholdLocationTests(TestCase):
    """Calendar Sources' household location must actually persist.

    Regression: HouseholdWriteSerializer accepted country/region/locality/postcode, but
    core.services.update_household's allow-list did not list them. The PATCH validated and
    returned 200 while the service silently dropped the values, so Settings appeared to save and
    reverted to "Not set" on the next load. The database is the source of truth here — these
    tests read it back rather than trusting the response body alone.
    """

    def setUp(self):
        self.admin = _make_user("admin3", role=User.Role.ADMIN)
        self.user = _make_user("user3")
        self.url = reverse("household")

    def _household(self):
        from apps.core.models import Household
        return Household.objects.order_by("id").first()

    def test_patch_persists_every_location_field(self):
        _login(self.client, "admin3")
        payload = {
            "country": "AU", "region": "QLD", "locality": "townsville", "postcode": "4810",
        }
        response = self.client.patch(self.url, payload, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        for field, value in payload.items():
            self.assertEqual(response.json()[field], value, f"{field} missing from response")

    def test_values_survive_a_fresh_database_fetch(self):
        """Not optimistic client state, not the serializer echo — the stored row."""
        _login(self.client, "admin3")
        self.client.patch(
            self.url,
            {"country": "AU", "region": "QLD", "locality": "townsville", "postcode": "4810"},
            content_type="application/json",
        )
        household = self._household()
        household.refresh_from_db()
        self.assertEqual(
            (household.country, household.region, household.locality, household.postcode),
            ("AU", "QLD", "townsville", "4810"),
        )

    def test_a_subsequent_get_returns_the_saved_location(self):
        _login(self.client, "admin3")
        self.client.patch(
            self.url,
            {"country": "AU", "region": "QLD", "locality": "brisbane", "postcode": "4000"},
            content_type="application/json",
        )
        data = self.client.get(self.url).json()
        self.assertEqual(data["country"], "AU")
        self.assertEqual(data["region"], "QLD")
        self.assertEqual(data["locality"], "brisbane")
        self.assertEqual(data["postcode"], "4000")

    def test_location_can_be_cleared_again(self):
        _login(self.client, "admin3")
        self.client.patch(
            self.url, {"country": "AU", "region": "QLD"}, content_type="application/json",
        )
        self.client.patch(
            self.url, {"country": "", "region": "", "locality": ""},
            content_type="application/json",
        )
        household = self._household()
        household.refresh_from_db()
        self.assertEqual((household.country, household.region, household.locality), ("", "", ""))

    def test_ordinary_household_fields_still_save(self):
        """The allow-list change must not have disturbed anything else."""
        _login(self.client, "admin3")
        response = self.client.patch(
            self.url,
            {"name": "The Test Household", "timezone": "Australia/Brisbane",
             "calendar_default_view": "week"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        household = self._household()
        household.refresh_from_db()
        self.assertEqual(household.name, "The Test Household")
        self.assertEqual(household.timezone, "Australia/Brisbane")
        self.assertEqual(household.calendar_default_view, "week")

    def test_a_partial_patch_leaves_other_location_fields_alone(self):
        _login(self.client, "admin3")
        self.client.patch(
            self.url,
            {"country": "AU", "region": "QLD", "locality": "cairns", "postcode": "4870"},
            content_type="application/json",
        )
        self.client.patch(self.url, {"locality": "brisbane"}, content_type="application/json")
        household = self._household()
        household.refresh_from_db()
        self.assertEqual(household.locality, "brisbane")
        self.assertEqual(household.region, "QLD")
        self.assertEqual(household.postcode, "4870")

    def test_non_admins_still_cannot_set_the_location(self):
        """Permissions are unchanged by widening the allow-list."""
        _login(self.client, "user3")
        response = self.client.patch(
            self.url, {"region": "VIC"}, content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        household = self._household()
        household.refresh_from_db()
        self.assertNotEqual(household.region, "VIC")

    def test_the_service_allow_list_covers_every_writable_serializer_field(self):
        """The structural guard for this whole class of bug.

        A field the write serializer accepts but the service ignores fails silently — the API
        answers 200 and nothing is saved. Rather than hope the two lists stay in step, assert it.
        """
        import inspect

        from apps.core.serializers import HouseholdWriteSerializer
        from apps.core import services

        writable = set(HouseholdWriteSerializer.Meta.fields)
        source = inspect.getsource(services.update_household)
        missing = [field for field in writable if f'"{field}"' not in source]
        self.assertEqual(
            missing, [],
            "HouseholdWriteSerializer accepts these fields but update_household would discard "
            f"them silently: {missing}",
        )
