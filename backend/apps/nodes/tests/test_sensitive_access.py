"""The shared sensitive-node gate. Permission tests first (D10).

Solace and Homestead used to carry a copy each, and the copies had drifted: Solace honoured
the household's `requires_reauthentication` setting, Homestead's finance surface ignored it.
These tests pin one behaviour for both, so a third node cannot introduce a fourth.
"""
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.nodes.access import node_requires_reauth
from apps.nodes.models import HouseholdNode, Node
from apps.nodes.services import enable_node


def _admin(username="gateadmin") -> User:
    user = User.objects.create_user(
        username=username, display_name="Gate admin", role=User.Role.ADMIN, password="pass123!"
    )
    user.set_pin("1234")
    user.save()
    return user


class SensitiveNodeGateTests(TestCase):
    def setUp(self):
        self.admin = _admin()
        enable_node(self.admin, "solace")
        enable_node(self.admin, "homestead")
        self.client.force_login(self.admin)

    def _reauth(self):
        return self.client.post(
            reverse("auth-reauth"), {"password": "pass123!"}, content_type="application/json"
        )

    def _set_reauth_required(self, node_key: str, required: bool):
        node = Node.objects.get(key=node_key)
        HouseholdNode.objects.filter(node=node).update(requires_reauthentication=required)

    # --- the lock itself ---

    def test_locked_node_is_denied_without_reauth(self):
        self._set_reauth_required("solace", True)
        response = self.client.get(reverse("solace-bill-list"))
        self.assertEqual(response.status_code, 403)

    def test_reauth_opens_the_node(self):
        self._set_reauth_required("solace", True)
        self._reauth()
        self.assertEqual(self.client.get(reverse("solace-bill-list")).status_code, 200)

    def test_household_can_turn_the_prompt_off(self):
        """An admin who trusts their own screen may disable the extra prompt (v0.19.0)."""
        self._set_reauth_required("solace", False)
        self.assertEqual(self.client.get(reverse("solace-bill-list")).status_code, 200)

    def test_homestead_finance_honours_the_same_setting(self):
        """The drift this module exists to remove: Homestead used to always prompt."""
        self._set_reauth_required("homestead", False)
        self.assertEqual(self.client.get(reverse("homestead-insurance-list")).status_code, 200)

    def test_homestead_finance_is_denied_when_the_prompt_is_on(self):
        self._set_reauth_required("homestead", True)
        self.assertEqual(self.client.get(reverse("homestead-insurance-list")).status_code, 403)

    # --- the resolver behind it ---

    def test_unknown_node_is_treated_as_locked(self):
        """A missing configuration row must not be a way past the gate."""
        self.assertTrue(node_requires_reauth("no-such-node"))

    def test_setting_is_read_from_the_household_not_the_catalogue(self):
        self._set_reauth_required("solace", False)
        self.assertFalse(node_requires_reauth("solace"))
        self._set_reauth_required("solace", True)
        self.assertTrue(node_requires_reauth("solace"))

    # --- the audit trail ---

    def test_every_read_is_audited(self):
        """Who looked at the household's finances matters as much as who changed them."""
        self._set_reauth_required("solace", True)
        self._reauth()
        AuditLog.objects.all().delete()
        self.client.get(reverse("solace-bill-list"))
        event = AuditLog.objects.filter(action="sensitive_node_accessed").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.metadata_json["node"], "solace")
        self.assertEqual(event.metadata_json["method"], "GET")

    def test_a_denied_attempt_is_not_recorded_as_access(self):
        self._set_reauth_required("solace", True)
        AuditLog.objects.all().delete()
        self.client.get(reverse("solace-bill-list"))
        self.assertFalse(
            AuditLog.objects.filter(action="sensitive_node_accessed").exists(),
            "a refused request never reached the data, so it is not an access",
        )


class LockedResponseContractTests(TestCase):
    """A refusal must tell a client what to do, not just that it failed.

    Each surface used to read the prose and invent its own locked state; the response now
    carries a code and the node key so one shared component can handle every sensitive node.
    """

    def setUp(self):
        self.admin = _admin("contractadmin")
        enable_node(self.admin, "solace")
        Node.objects.filter(key="solace").update(supports_sensitive_lock=True)
        HouseholdNode.objects.filter(node__key="solace").update(requires_reauthentication=True)
        self.client.force_login(self.admin)

    def test_locked_response_is_machine_readable(self):
        response = self.client.get(reverse("solace-bill-list"))
        self.assertEqual(response.status_code, 403)
        body = response.json()
        self.assertEqual(body["code"], "reauth_required")
        self.assertEqual(body["node"], "solace")
        self.assertTrue(body["detail"])

    def test_a_plain_permission_failure_is_not_marked_as_locked(self):
        """Lacking permission is a different answer from being locked, and must read as one."""
        member = User.objects.create_user(
            username="plainmember", display_name="Member", role=User.Role.USER, password="pass123!"
        )
        member.set_pin("1234")
        member.save()
        self.client.force_login(member)
        self.client.post(
            reverse("auth-reauth"), {"password": "pass123!"}, content_type="application/json"
        )
        response = self.client.get(reverse("solace-bill-list"))
        self.assertIn(response.status_code, [401, 403])
        self.assertNotEqual(response.json().get("code"), "reauth_required")
