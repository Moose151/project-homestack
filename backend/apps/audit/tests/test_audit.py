"""
Audit log tests — Phase 1.6, written FIRST per D10.

Covers:
- log_audit() creates an AuditLog row
- Login and failed-login create audit rows
- GET /api/v1/audit-logs/ is admin-only
"""
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.core.models import get_active_household


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


class AuditHelperTests(TestCase):
    def test_log_audit_creates_row(self):
        from apps.audit.helpers import log_audit
        from apps.audit.models import AuditLog
        user = _make_user("actor")
        log_audit("test_action", user=user)
        self.assertEqual(AuditLog.objects.filter(action="test_action").count(), 1)

    def test_log_audit_captures_user(self):
        from apps.audit.helpers import log_audit
        from apps.audit.models import AuditLog
        user = _make_user("actor2")
        log_audit("test_action2", user=user)
        log = AuditLog.objects.get(action="test_action2")
        self.assertEqual(log.user, user)

    def test_log_audit_no_user(self):
        from apps.audit.helpers import log_audit
        from apps.audit.models import AuditLog
        log_audit("system_action")
        self.assertEqual(AuditLog.objects.filter(action="system_action").count(), 1)

    def test_log_audit_captures_household(self):
        from apps.audit.helpers import log_audit
        from apps.audit.models import AuditLog
        log_audit("hh_action")
        log = AuditLog.objects.get(action="hh_action")
        self.assertEqual(log.household, get_active_household())

    def test_log_audit_with_metadata(self):
        from apps.audit.helpers import log_audit
        from apps.audit.models import AuditLog
        log_audit("meta_action", metadata={"key": "value"})
        log = AuditLog.objects.get(action="meta_action")
        self.assertEqual(log.metadata_json["key"], "value")


class AuditLoginLoggingTests(TestCase):
    """Login and failed-login should produce audit rows."""

    def setUp(self):
        self.user = _make_user("audited", pin="9999")

    def test_successful_pin_login_logged(self):
        from apps.audit.models import AuditLog
        self.client.post(reverse("auth-pin-login"), {"username": "audited", "pin": "9999"},
                         content_type="application/json")
        self.assertTrue(AuditLog.objects.filter(action="login", user=self.user).exists())

    def test_failed_pin_login_logged(self):
        from apps.audit.models import AuditLog
        self.client.post(reverse("auth-pin-login"), {"username": "audited", "pin": "0000"},
                         content_type="application/json")
        self.assertTrue(AuditLog.objects.filter(action="login_failed").exists())


class AuditLogListViewTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", role=User.Role.ADMIN)
        self.user = _make_user("user")
        self.url = reverse("audit-logs-list")

    def test_unauthenticated_denied(self):
        resp = self.client.get(self.url)
        self.assertIn(resp.status_code, [401, 403])

    def test_admin_can_list(self):
        _login(self.client, "admin")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_user_cannot_list(self):
        _login(self.client, "user")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)
