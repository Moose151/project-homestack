"""
Permission integration tests — People API matrix (Phase 1.5, D10).

Tests that the DRF permission class + resolver correctly gate the People endpoints.
Written before wiring HomeStackPermission into the people views.

Matrix:
                   GET /people/   POST /people/   PATCH /{id}/   DELETE /{id}/
unauthenticated        401             401            401            401
admin                  200             201            200            204
manager                200             201            200            204
user (regular)         200             403            403            403
guest                  200             403            403            403
child account          200             403            403            403
"""
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.people.models import Person
from apps.people.services import create_person


def _make_user(username, role=User.Role.USER, is_child=False, pin="1234") -> User:
    user = User.objects.create_user(
        username=username,
        display_name=username.title(),
        password="pass!",
        role=role,
        is_child_account=is_child,
    )
    user.set_pin(pin)
    user.save()
    return user


def _login(client, username, pin="1234"):
    client.post(
        reverse("auth-pin-login"),
        {"username": username, "pin": pin},
        content_type="application/json",
    )


def _make_person(acting_user, display_name="Test Person") -> Person:
    return create_person(acting_user, display_name=display_name, profile_type=Person.ProfileType.ADULT)


class PeopleListPermissionTests(TestCase):
    """GET /people/ and POST /people/"""

    def setUp(self):
        self.list_url = reverse("people-list")
        self.admin = _make_user("admin", role=User.Role.ADMIN)
        self.manager = _make_user("manager", role=User.Role.MANAGER)
        self.user = _make_user("user")
        self.guest = _make_user("guest", role=User.Role.GUEST)
        self.child = _make_user("child", is_child=True)

    # GET /people/
    def test_unauthenticated_list_denied(self):
        resp = self.client.get(self.list_url)
        self.assertIn(resp.status_code, [401, 403])

    def test_admin_can_list(self):
        _login(self.client, "admin")
        self.assertEqual(self.client.get(self.list_url).status_code, 200)

    def test_manager_can_list(self):
        _login(self.client, "manager")
        self.assertEqual(self.client.get(self.list_url).status_code, 200)

    def test_user_can_list(self):
        _login(self.client, "user")
        self.assertEqual(self.client.get(self.list_url).status_code, 200)

    def test_guest_can_list(self):
        _login(self.client, "guest")
        self.assertEqual(self.client.get(self.list_url).status_code, 200)

    def test_child_can_list(self):
        _login(self.client, "child")
        self.assertEqual(self.client.get(self.list_url).status_code, 200)

    # POST /people/
    def test_unauthenticated_create_denied(self):
        resp = self.client.post(
            self.list_url,
            {"display_name": "X", "profile_type": "adult"},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [401, 403])

    def test_admin_can_create(self):
        _login(self.client, "admin")
        resp = self.client.post(
            self.list_url,
            {"display_name": "New Person", "profile_type": "adult"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_manager_can_create(self):
        _login(self.client, "manager")
        resp = self.client.post(
            self.list_url,
            {"display_name": "New Person", "profile_type": "adult"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_user_cannot_create(self):
        _login(self.client, "user")
        resp = self.client.post(
            self.list_url,
            {"display_name": "New Person", "profile_type": "adult"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_guest_cannot_create(self):
        _login(self.client, "guest")
        resp = self.client.post(
            self.list_url,
            {"display_name": "New Person", "profile_type": "adult"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_child_cannot_create(self):
        _login(self.client, "child")
        resp = self.client.post(
            self.list_url,
            {"display_name": "New Person", "profile_type": "adult"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)


class PeopleDetailPermissionTests(TestCase):
    """PATCH /people/{id}/ and DELETE /people/{id}/"""

    def setUp(self):
        self.admin = _make_user("admin2", role=User.Role.ADMIN)
        self.manager = _make_user("manager2", role=User.Role.MANAGER)
        self.user = _make_user("user2")
        self.guest = _make_user("guest2", role=User.Role.GUEST)
        self.child = _make_user("child2", is_child=True)
        self.person = _make_person(self.admin)
        self.detail_url = reverse("people-detail", kwargs={"person_id": self.person.pk})

    # PATCH
    def test_unauthenticated_patch_denied(self):
        resp = self.client.patch(
            self.detail_url, {"display_name": "X"}, content_type="application/json"
        )
        self.assertIn(resp.status_code, [401, 403])

    def test_admin_can_patch(self):
        _login(self.client, "admin2")
        resp = self.client.patch(
            self.detail_url, {"display_name": "Updated"}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)

    def test_manager_can_patch(self):
        _login(self.client, "manager2")
        resp = self.client.patch(
            self.detail_url, {"display_name": "Updated"}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)

    def test_user_cannot_patch(self):
        _login(self.client, "user2")
        resp = self.client.patch(
            self.detail_url, {"display_name": "Updated"}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_guest_cannot_patch(self):
        _login(self.client, "guest2")
        resp = self.client.patch(
            self.detail_url, {"display_name": "Updated"}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_child_cannot_patch(self):
        _login(self.client, "child2")
        resp = self.client.patch(
            self.detail_url, {"display_name": "Updated"}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 403)

    # DELETE
    def test_unauthenticated_delete_denied(self):
        resp = self.client.delete(self.detail_url)
        self.assertIn(resp.status_code, [401, 403])

    def test_admin_can_delete(self):
        _login(self.client, "admin2")
        resp = self.client.delete(self.detail_url)
        self.assertEqual(resp.status_code, 204)

    def test_manager_can_delete(self):
        person2 = _make_person(self.admin, display_name="Extra Person")
        url = reverse("people-detail", kwargs={"person_id": person2.pk})
        _login(self.client, "manager2")
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, 204)

    def test_user_cannot_delete(self):
        _login(self.client, "user2")
        resp = self.client.delete(self.detail_url)
        self.assertEqual(resp.status_code, 403)

    def test_guest_cannot_delete(self):
        _login(self.client, "guest2")
        resp = self.client.delete(self.detail_url)
        self.assertEqual(resp.status_code, 403)

    def test_child_cannot_delete(self):
        _login(self.client, "child2")
        resp = self.client.delete(self.detail_url)
        self.assertEqual(resp.status_code, 403)
