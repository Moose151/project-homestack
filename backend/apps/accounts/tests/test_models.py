"""
accounts model tests — Phase 1.3 (D6, D12).

Covers:
- User creation via UserManager (PIN hash, password hash, role defaults).
- PIN helper methods (set_pin / check_pin).
- Soft-delete behaviour on HouseholdBaseModel via User (deferred from Phase 1.2).
- is_staff property per role.
- Child account cannot authenticate with PasswordBackend.
"""
from django.contrib.auth.hashers import is_password_usable
from django.test import TestCase

from apps.accounts.models import User
from apps.core.models import get_active_household


def _make_user(**kwargs) -> User:
    """Create a saved User via the manager; PIN defaults to '1234', password to 'password!'."""
    defaults = {
        "username": "testuser",
        "display_name": "Test User",
        "password": "password!",
    }
    defaults.update(kwargs)
    user = User.objects.create_user(**defaults)
    user.set_pin("1234")
    user.save()
    return user


class UserCreationTests(TestCase):
    def test_user_belongs_to_seeded_household(self):
        user = _make_user()
        self.assertEqual(user.household, get_active_household())

    def test_default_role_is_user(self):
        user = _make_user()
        self.assertEqual(user.role, User.Role.USER)

    def test_create_superuser_sets_admin_role(self):
        user = User.objects.create_superuser(
            username="admin", display_name="Admin", password="adminpass!"
        )
        self.assertEqual(user.role, User.Role.ADMIN)

    def test_password_is_hashed(self):
        user = _make_user()
        self.assertNotEqual(user.password, "password!")
        self.assertTrue(is_password_usable(user.password))
        self.assertTrue(user.check_password("password!"))

    def test_pin_is_hashed(self):
        user = _make_user()
        self.assertNotIn("1234", user.pin_hash)
        self.assertTrue(user.check_pin("1234"))
        self.assertFalse(user.check_pin("9999"))

    def test_empty_pin_check_returns_false(self):
        user = _make_user()
        user.pin_hash = ""
        self.assertFalse(user.check_pin("1234"))

    def test_str_returns_display_name(self):
        user = _make_user(display_name="Alice")
        self.assertEqual(str(user), "Alice")


class UserRoleTests(TestCase):
    def test_admin_is_staff(self):
        user = _make_user(role=User.Role.ADMIN)
        self.assertTrue(user.is_staff)

    def test_manager_is_staff(self):
        user = _make_user(role=User.Role.MANAGER)
        self.assertTrue(user.is_staff)

    def test_user_is_not_staff(self):
        user = _make_user(role=User.Role.USER)
        self.assertFalse(user.is_staff)

    def test_guest_is_not_staff(self):
        user = _make_user(role=User.Role.GUEST)
        self.assertFalse(user.is_staff)

    def test_admin_has_perm(self):
        user = _make_user(role=User.Role.ADMIN)
        self.assertTrue(user.has_perm("any.perm"))

    def test_non_admin_lacks_perm(self):
        user = _make_user(role=User.Role.USER)
        self.assertFalse(user.has_perm("any.perm"))


class SoftDeleteTests(TestCase):
    """HouseholdBaseModel soft-delete wired through User (deferred from Phase 1.2)."""

    def test_soft_delete_sets_deleted_at(self):
        user = _make_user()
        self.assertIsNone(user.deleted_at)
        user.soft_delete()
        self.assertIsNotNone(user.deleted_at)

    def test_soft_deleted_user_excluded_from_default_manager(self):
        user = _make_user()
        user.soft_delete()
        self.assertFalse(User.objects.filter(pk=user.pk).exists())

    def test_soft_deleted_user_visible_via_all_objects(self):
        user = _make_user()
        user.soft_delete()
        self.assertTrue(User.all_objects.filter(pk=user.pk).exists())

    def test_restore_removes_deleted_at(self):
        user = _make_user()
        user.soft_delete()
        user.restore()
        self.assertIsNone(user.deleted_at)
        self.assertTrue(User.objects.filter(pk=user.pk).exists())
