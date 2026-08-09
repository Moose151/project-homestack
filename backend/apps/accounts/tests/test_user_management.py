"""User-management tests (admin-only account CRUD)."""
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.people.models import Person
from apps.permissions.models import UserPermission
from apps.permissions.resolver import resolve_permission
from apps.permissions.services import grant_user_permission


def _make_user(username, role=User.Role.ADMIN, is_child=False):
    u = User.objects.create_user(username=username, display_name=username.capitalize(), role=role, password="pass123!")
    u.set_pin("1234")
    u.is_child_account = is_child
    u.save()
    return u


def _login(client, username, pin="1234"):
    client.post(reverse("auth-pin-login"), {"username": username, "pin": pin}, content_type="application/json")


def _person(name):
    from apps.core.models import get_active_household
    return Person.objects.create(household=get_active_household(), display_name=name,
                                 profile_type=Person.ProfileType.CHILD)


class UserManagementPermissionTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", role=User.Role.ADMIN)
        self.manager = _make_user("manager", role=User.Role.MANAGER)
        self.url = reverse("user-list")

    def test_admin_can_list(self):
        _login(self.client, "admin")
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_manager_cannot_list(self):
        _login(self.client, "manager")
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_unauthenticated_denied(self):
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_manager_cannot_create(self):
        _login(self.client, "manager")
        resp = self.client.post(self.url, {"username": "x", "display_name": "X", "pin": "1234"},
                                content_type="application/json")
        self.assertEqual(resp.status_code, 403)


class UserManagementCRUDTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", role=User.Role.ADMIN)
        _login(self.client, "admin")
        self.url = reverse("user-list")

    def test_create_user_with_new_person(self):
        resp = self.client.post(self.url, {
            "username": "kid1", "display_name": "Finn", "role": "user", "pin": "4321",
            "is_child_account": True, "create_person": True,
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 201)
        user = User.objects.get(username="kid1")
        self.assertTrue(user.check_pin("4321"))
        self.assertTrue(user.is_child_account)
        person = Person.objects.get(linked_user=user)
        self.assertEqual(person.display_name, "Finn")
        self.assertEqual(person.profile_type, Person.ProfileType.CHILD)

    def test_create_user_linking_existing_person(self):
        person = _person("Mara")
        resp = self.client.post(self.url, {
            "username": "mara", "display_name": "Mara", "role": "user", "pin": "4321",
            "link_person_id": person.id,
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 201)
        person.refresh_from_db()
        self.assertEqual(person.linked_user.username, "mara")

    def test_duplicate_username_rejected(self):
        resp = self.client.post(self.url, {"username": "admin", "display_name": "Dupe", "pin": "4321"},
                                content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_invalid_pin_rejected(self):
        resp = self.client.post(self.url, {"username": "bad", "display_name": "Bad", "pin": "12"},
                                content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_edit_role_and_reset_pin(self):
        target = _make_user("bob", role=User.Role.USER)
        url = reverse("user-detail", args=[target.id])
        resp = self.client.patch(url, {"role": "manager", "pin": "9999"}, content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        target.refresh_from_db()
        self.assertEqual(target.role, "manager")
        self.assertTrue(target.check_pin("9999"))

    def test_create_manager_with_money_access_grants_solace_without_admin_role(self):
        resp = self.client.post(
            self.url,
            {
                "username": "partner",
                "display_name": "Partner",
                "role": "manager",
                "pin": "4321",
                "password": "partner-password!",
                "solace_access": True,
                "create_person": True,
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.json()["solace_access"])
        partner = User.objects.get(username="partner")
        self.assertEqual(partner.role, User.Role.MANAGER)
        for action in ("view", "create", "edit", "delete"):
            self.assertTrue(resolve_permission(partner, action, "solace"))
        self.assertTrue(
            AuditLog.objects.filter(
                action="user_money_access_updated",
                target_record_type="User",
                target_record_id=partner.id,
            ).exists()
        )

    def test_money_access_can_be_removed_and_reverts_to_role_default(self):
        target = _make_user("partner", role=User.Role.MANAGER)
        url = reverse("user-detail", args=[target.id])
        grant = self.client.patch(url, {"solace_access": True}, content_type="application/json")
        self.assertEqual(grant.status_code, 200)
        self.assertTrue(grant.json()["solace_access"])
        self.assertEqual(
            UserPermission.objects.filter(user=target, permission__scope="solace", is_granted=True).count(),
            4,
        )

        clear = self.client.patch(url, {"solace_access": False}, content_type="application/json")
        self.assertEqual(clear.status_code, 200)
        self.assertFalse(clear.json()["solace_access"])
        self.assertFalse(UserPermission.objects.filter(user=target, permission__scope="solace").exists())
        self.assertFalse(resolve_permission(target, "view", "solace"))

    def test_child_account_cannot_receive_money_access(self):
        resp = self.client.post(
            self.url,
            {
                "username": "child-money",
                "display_name": "Child",
                "role": "user",
                "is_child_account": True,
                "pin": "4321",
                "solace_access": True,
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(User.all_objects.filter(username="child-money").exists())

    def test_child_account_cannot_be_created_with_adult_role(self):
        resp = self.client.post(
            self.url,
            {
                "username": "child-admin",
                "display_name": "Child",
                "role": "admin",
                "is_child_account": True,
                "pin": "4321",
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(User.all_objects.filter(username="child-admin").exists())

    def test_existing_child_cannot_be_promoted_to_adult_role(self):
        child = _make_user("child-role", role=User.Role.USER, is_child=True)
        resp = self.client.patch(
            reverse("user-detail", args=[child.id]),
            {"role": "manager"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        child.refresh_from_db()
        self.assertEqual(child.role, User.Role.USER)

    def test_converting_adult_to_child_clears_existing_money_access(self):
        target = _make_user("adult-to-child", role=User.Role.MANAGER)
        for action in ("view", "create", "edit", "delete"):
            grant_user_permission(target, f"solace.{action}")
        resp = self.client.patch(
            reverse("user-detail", args=[target.id]),
            {"role": "user", "is_child_account": True},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        target.refresh_from_db()
        self.assertTrue(target.is_child_account)
        self.assertFalse(resolve_permission(target, "view", "solace"))
        self.assertFalse(UserPermission.objects.filter(user=target, permission__scope="solace").exists())

    def test_manager_needs_password_before_money_access(self):
        resp = self.client.post(
            self.url,
            {
                "username": "no-password-partner",
                "display_name": "Partner",
                "role": "manager",
                "pin": "4321",
                "solace_access": True,
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(User.all_objects.filter(username="no-password-partner").exists())

    def test_reset_own_password_preserves_session_and_allows_reauth(self):
        resp = self.client.patch(
            reverse("user-detail", args=[self.admin.id]),
            {"password": "new-admin-password!"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("new-admin-password!"))
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(
            self.client.post(
                reverse("auth-reauth"),
                {"password": "new-admin-password!"},
                content_type="application/json",
            ).status_code,
            200,
        )

    def test_deactivate_user(self):
        target = _make_user("bob", role=User.Role.USER)
        resp = self.client.delete(reverse("user-detail", args=[target.id]))
        self.assertEqual(resp.status_code, 204)
        # Deactivation disables login but preserves the record (and its history).
        target.refresh_from_db()
        self.assertFalse(target.is_active)

    def test_cannot_deactivate_self(self):
        resp = self.client.delete(reverse("user-detail", args=[self.admin.id]))
        self.assertEqual(resp.status_code, 400)


class UserColourPropagationTests(TestCase):
    """A user's colour should flow to their linked Person so it shows on calendar items."""

    def setUp(self):
        self.admin = _make_user("admin", role=User.Role.ADMIN)
        _login(self.client, "admin")

    def test_create_with_person_copies_colour(self):
        resp = self.client.post(
            reverse("user-list"),
            {"username": "kid", "display_name": "Kid", "pin": "4321",
             "colour": "#123456", "create_person": True},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        person = Person.objects.get(linked_user__username="kid")
        self.assertEqual(person.colour, "#123456")

    def test_update_colour_propagates_to_linked_person(self):
        self.client.post(
            reverse("user-list"),
            {"username": "kid", "display_name": "Kid", "pin": "4321", "create_person": True},
            content_type="application/json",
        )
        target = User.objects.get(username="kid")
        resp = self.client.patch(
            reverse("user-detail", args=[target.id]),
            {"colour": "#abcdef"}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        person = Person.objects.get(linked_user=target)
        self.assertEqual(person.colour, "#abcdef")
