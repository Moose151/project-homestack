"""User-management tests (admin-only account CRUD)."""
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.people.models import Person


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
