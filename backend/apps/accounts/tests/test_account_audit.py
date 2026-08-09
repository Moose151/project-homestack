"""Account and permission changes must leave an audit trail (Milestone 4, Security §11).

Granting Money access was already recorded, but creating a login, changing someone's access
level, resetting their PIN or password, deactivating them, and granting or denying a permission
directly were not — so the most security-relevant actions in the product were the least
traceable. Credential values are never recorded, only the fact that they changed.
"""
from django.test import TestCase

from apps.accounts.models import User
from apps.accounts.user_services import (
    create_user_account,
    deactivate_user,
    update_user_account,
)
from apps.audit.models import AuditLog
from apps.permissions.services import (
    clear_user_permission,
    deny_user_permission,
    grant_user_permission,
)


def _admin() -> User:
    user = User.objects.create_user(
        username="auditadmin", display_name="Audit admin", role=User.Role.ADMIN, password="pass123!"
    )
    user.set_pin("1234")
    user.save()
    return user


class AccountChangeAuditTests(TestCase):
    def setUp(self):
        self.admin = _admin()
        AuditLog.objects.all().delete()

    def _events(self, action: str):
        return AuditLog.objects.filter(action=action)

    def test_creating_a_login_is_recorded(self):
        create_user_account(
            self.admin, username="partner", display_name="Partner", pin="4321"
        )
        event = self._events("user_created").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.metadata_json["username"], "partner")

    def test_changing_access_level_is_recorded_with_both_values(self):
        user = create_user_account(self.admin, username="p2", display_name="P2")
        AuditLog.objects.all().delete()
        update_user_account(self.admin, user, role=User.Role.MANAGER)
        event = self._events("user_role_changed").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.metadata_json["from"], User.Role.USER)
        self.assertEqual(event.metadata_json["to"], User.Role.MANAGER)

    def test_unchanged_role_is_not_recorded(self):
        user = create_user_account(self.admin, username="p3", display_name="P3")
        AuditLog.objects.all().delete()
        update_user_account(self.admin, user, display_name="P3 renamed")
        self.assertFalse(self._events("user_role_changed").exists())

    def test_credential_reset_is_recorded_without_the_credential(self):
        user = create_user_account(self.admin, username="p4", display_name="P4")
        AuditLog.objects.all().delete()
        update_user_account(self.admin, user, pin="9876", password="new-secret")
        event = self._events("user_credentials_changed").first()
        self.assertIsNotNone(event)
        self.assertEqual(sorted(event.metadata_json["changed"]), ["password", "pin"])
        recorded = str(event.metadata_json)
        self.assertNotIn("9876", recorded)
        self.assertNotIn("new-secret", recorded)

    def test_deactivation_is_recorded(self):
        user = create_user_account(self.admin, username="p5", display_name="P5")
        AuditLog.objects.all().delete()
        deactivate_user(self.admin, user)
        self.assertTrue(self._events("user_deactivated").exists())


class PermissionChangeAuditTests(TestCase):
    def setUp(self):
        self.admin = _admin()
        self.member = User.objects.create_user(
            username="member", display_name="Member", role=User.Role.USER
        )
        AuditLog.objects.all().delete()

    def test_granting_a_permission_is_recorded(self):
        grant_user_permission(self.member, "solace.view", acting_user=self.admin)
        event = AuditLog.objects.filter(action="permission_granted").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.metadata_json["permission"], "solace.view")
        self.assertEqual(event.metadata_json["target_user"], "member")

    def test_denying_a_permission_is_recorded(self):
        deny_user_permission(self.member, "solace.view", acting_user=self.admin)
        event = AuditLog.objects.filter(action="permission_denied").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.metadata_json["permission"], "solace.view")

    def test_clearing_an_override_is_recorded(self):
        grant_user_permission(self.member, "solace.view", acting_user=self.admin)
        AuditLog.objects.all().delete()
        clear_user_permission(self.member, "solace.view", acting_user=self.admin)
        self.assertTrue(AuditLog.objects.filter(action="permission_cleared").exists())

    def test_clearing_nothing_records_nothing(self):
        clear_user_permission(self.member, "solace.view", acting_user=self.admin)
        self.assertFalse(AuditLog.objects.filter(action="permission_cleared").exists())
