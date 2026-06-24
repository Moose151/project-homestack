"""
Permission resolver tests — Phase 1.5, written FIRST per D10.

Tests the central resolve_permission(user, action, resource) function.
Seed data (roles, default role_permissions) is applied by migrations before the suite runs.

Coverage:
- Unauthenticated / inactive users → deny
- admin/manager → allow all people.* actions
- user/guest → allow only people.view
- child account (is_child_account=True) → view only regardless of role
- Per-user explicit grant overrides role default (user can create)
- Per-user explicit deny overrides role default (admin cannot delete)
"""
from django.test import TestCase

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.permissions.models import Permission, UserPermission
from apps.permissions.resolver import resolve_permission


def _make_user(username, role=User.Role.USER, is_child=False, is_active=True) -> User:
    user = User.objects.create_user(
        username=username,
        display_name=username.title(),
        password="pass!",
        role=role,
        is_child_account=is_child,
    )
    if not is_active:
        user.is_active = False
        user.save(update_fields=["is_active"])
    return user


def _grant(user, codename: str) -> None:
    perm = Permission.objects.get(code=codename)
    UserPermission.objects.update_or_create(
        user=user,
        permission=perm,
        defaults={"is_granted": True, "household": get_active_household()},
    )


def _deny(user, codename: str) -> None:
    perm = Permission.objects.get(code=codename)
    UserPermission.objects.update_or_create(
        user=user,
        permission=perm,
        defaults={"is_granted": False, "household": get_active_household()},
    )


class UnauthenticatedTests(TestCase):
    def test_anonymous_user_denied(self):
        class Anon:
            is_authenticated = False

        for action in ("view", "create", "edit", "delete"):
            with self.subTest(action=action):
                self.assertFalse(resolve_permission(Anon(), action, "people"))

    def test_none_user_denied(self):
        self.assertFalse(resolve_permission(None, "view", "people"))

    def test_inactive_user_denied(self):
        user = _make_user("inactive", is_active=False)
        self.assertFalse(resolve_permission(user, "view", "people"))


class AdminPermissionTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", role=User.Role.ADMIN)

    def test_admin_can_view(self):
        self.assertTrue(resolve_permission(self.admin, "view", "people"))

    def test_admin_can_create(self):
        self.assertTrue(resolve_permission(self.admin, "create", "people"))

    def test_admin_can_edit(self):
        self.assertTrue(resolve_permission(self.admin, "edit", "people"))

    def test_admin_can_delete(self):
        self.assertTrue(resolve_permission(self.admin, "delete", "people"))


class ManagerPermissionTests(TestCase):
    def setUp(self):
        self.manager = _make_user("manager", role=User.Role.MANAGER)

    def test_manager_can_view(self):
        self.assertTrue(resolve_permission(self.manager, "view", "people"))

    def test_manager_can_create(self):
        self.assertTrue(resolve_permission(self.manager, "create", "people"))

    def test_manager_can_edit(self):
        self.assertTrue(resolve_permission(self.manager, "edit", "people"))

    def test_manager_can_delete(self):
        self.assertTrue(resolve_permission(self.manager, "delete", "people"))


class UserPermissionTests(TestCase):
    def setUp(self):
        self.user = _make_user("regularuser", role=User.Role.USER)

    def test_user_can_view(self):
        self.assertTrue(resolve_permission(self.user, "view", "people"))

    def test_user_cannot_create(self):
        self.assertFalse(resolve_permission(self.user, "create", "people"))

    def test_user_cannot_edit(self):
        self.assertFalse(resolve_permission(self.user, "edit", "people"))

    def test_user_cannot_delete(self):
        self.assertFalse(resolve_permission(self.user, "delete", "people"))


class GuestPermissionTests(TestCase):
    def setUp(self):
        self.guest = _make_user("guestuser", role=User.Role.GUEST)

    def test_guest_can_view(self):
        self.assertTrue(resolve_permission(self.guest, "view", "people"))

    def test_guest_cannot_create(self):
        self.assertFalse(resolve_permission(self.guest, "create", "people"))

    def test_guest_cannot_edit(self):
        self.assertFalse(resolve_permission(self.guest, "edit", "people"))

    def test_guest_cannot_delete(self):
        self.assertFalse(resolve_permission(self.guest, "delete", "people"))


class ChildAccountPermissionTests(TestCase):
    """Children are blocked from all writes regardless of their role (kiosk safety)."""

    def setUp(self):
        self.child = _make_user("child1", role=User.Role.USER, is_child=True)

    def test_child_can_view(self):
        self.assertTrue(resolve_permission(self.child, "view", "people"))

    def test_child_cannot_create(self):
        self.assertFalse(resolve_permission(self.child, "create", "people"))

    def test_child_cannot_edit(self):
        self.assertFalse(resolve_permission(self.child, "edit", "people"))

    def test_child_cannot_delete(self):
        self.assertFalse(resolve_permission(self.child, "delete", "people"))


class UserPermissionOverrideTests(TestCase):
    """Per-user overrides take precedence over the role default."""

    def setUp(self):
        self.user = _make_user("overrideuser", role=User.Role.USER)
        self.admin = _make_user("adminover", role=User.Role.ADMIN)

    def test_explicit_grant_allows_user_to_create(self):
        _grant(self.user, "people.create")
        self.assertTrue(resolve_permission(self.user, "create", "people"))

    def test_explicit_deny_blocks_admin_from_deleting(self):
        _deny(self.admin, "people.delete")
        self.assertFalse(resolve_permission(self.admin, "delete", "people"))

    def test_explicit_grant_still_allows_base_role_view(self):
        _grant(self.user, "people.create")
        self.assertTrue(resolve_permission(self.user, "view", "people"))

    def test_explicit_deny_does_not_affect_other_actions(self):
        _deny(self.admin, "people.delete")
        self.assertTrue(resolve_permission(self.admin, "edit", "people"))

    def test_unknown_resource_denied(self):
        self.assertFalse(resolve_permission(self.admin, "view", "nonexistent_resource"))
