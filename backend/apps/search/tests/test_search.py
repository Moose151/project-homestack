from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.atlas.models import AtlasNote
from apps.core.models import get_active_household
from apps.nodes.models import HouseholdNode
from apps.scheduling.models import CalendarEvent


class GlobalSearchTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin",
            display_name="Admin",
            role=User.Role.ADMIN,
            password="admin-password!",
        )
        self.user.set_pin("1234")
        self.user.save(update_fields=["pin_hash"])
        self.client.post(
            reverse("auth-pin-login"),
            {"username": "admin", "pin": "1234"},
            content_type="application/json",
        )
        HouseholdNode.objects.filter(node__key__in=["atlas", "solace"]).update(
            is_enabled=True,
            is_hidden=False,
        )
        household = get_active_household()
        AtlasNote.objects.create(
            household=household,
            title="Solar quote",
            body="Compare installers",
            created_by=self.user,
            updated_by=self.user,
        )
        CalendarEvent.objects.create(
            household=household,
            title="Solar installer visit",
            start_at=timezone.now(),
            created_by=self.user,
            updated_by=self.user,
        )
        self.url = reverse("global-search")

    def test_search_combines_calendar_and_enabled_nodes(self):
        response = self.client.get(self.url, {"q": "solar"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("app;dur=", response.headers["Server-Timing"])
        nodes = {row["node"] for row in response.json()["results"]}
        self.assertIn("calendar", nodes)
        self.assertIn("atlas", nodes)

    def test_sensitive_node_is_reported_locked_until_reauth(self):
        response = self.client.get(self.url, {"q": "solar"})
        self.assertIn("solace", response.json()["locked_nodes"])
        self.client.post(
            reverse("auth-reauth"),
            {"password": "admin-password!"},
            content_type="application/json",
        )
        response = self.client.get(self.url, {"q": "solar"})
        self.assertNotIn("solace", response.json()["locked_nodes"])

    def test_unauthenticated_search_is_denied(self):
        self.client.post(reverse("auth-logout"))
        self.assertIn(self.client.get(self.url).status_code, {401, 403})
