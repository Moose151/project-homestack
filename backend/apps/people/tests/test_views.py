"""
people endpoint tests — Phase 1.4 (API spec §3).

Tests cover:
- Unauthenticated requests are rejected (401).
- GET /people/ returns list.
- POST /people/ creates a person.
- GET /people/{id}/ returns detail.
- PATCH /people/{id}/ updates fields.
- DELETE /people/{id}/ soft-deletes (204, then 404 on re-fetch).
- 404 for unknown/soft-deleted person.
"""
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.people.models import Person
from apps.people.services import create_person


def _make_user(username="alice", display_name="Alice", role=User.Role.ADMIN,
               pin="1234", password="alicepass!") -> User:
    user = User.objects.create_user(
        username=username, display_name=display_name, role=role, password=password
    )
    user.set_pin(pin)
    user.save()
    return user


def _make_person(acting_user, **kwargs) -> Person:
    defaults = {"display_name": "Test Person", "profile_type": Person.ProfileType.ADULT}
    defaults.update(kwargs)
    return create_person(acting_user, **defaults)


def _login(client, username="alice", pin="1234"):
    client.post(
        reverse("auth-pin-login"),
        {"username": username, "pin": pin},
        content_type="application/json",
    )


class PeopleListViewTests(TestCase):
    def setUp(self):
        self.user = _make_user()
        self.url = reverse("people-list")

    def test_unauthenticated_returns_403(self):
        resp = self.client.get(self.url)
        self.assertIn(resp.status_code, [401, 403])

    def test_authenticated_list_empty(self):
        _login(self.client)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_authenticated_list_returns_people(self):
        _make_person(self.user, display_name="Alice")
        _make_person(self.user, display_name="Bob")
        _login(self.client)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        names = [p["display_name"] for p in resp.json()]
        self.assertIn("Alice", names)
        self.assertIn("Bob", names)

    def test_post_creates_person(self):
        _login(self.client)
        payload = {
            "display_name": "Finn",
            "profile_type": "child",
            "preferred_name": "Fi",
            "colour": "#FF0000",
        }
        resp = self.client.post(self.url, payload, content_type="application/json")
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["display_name"], "Finn")
        self.assertEqual(data["profile_type"], "child")
        self.assertEqual(data["preferred_name"], "Fi")

    def test_post_unauthenticated_returns_403(self):
        resp = self.client.post(
            self.url,
            {"display_name": "X", "profile_type": "adult"},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [401, 403])

    def test_post_missing_display_name_returns_400(self):
        _login(self.client)
        resp = self.client.post(
            self.url, {"profile_type": "adult"}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_post_blank_display_name_returns_400(self):
        _login(self.client)
        resp = self.client.post(
            self.url, {"display_name": "   ", "profile_type": "adult"}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_soft_deleted_person_not_in_list(self):
        person = _make_person(self.user, display_name="Gone")
        person.soft_delete()
        _login(self.client)
        resp = self.client.get(self.url)
        names = [p["display_name"] for p in resp.json()]
        self.assertNotIn("Gone", names)


class PeopleDetailViewTests(TestCase):
    def setUp(self):
        self.user = _make_user()
        self.person = _make_person(self.user, display_name="Alice")
        self.url = lambda pk: reverse("people-detail", kwargs={"person_id": pk})

    def test_unauthenticated_returns_403(self):
        resp = self.client.get(self.url(self.person.pk))
        self.assertIn(resp.status_code, [401, 403])

    def test_get_returns_detail(self):
        _login(self.client)
        resp = self.client.get(self.url(self.person.pk))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["display_name"], "Alice")

    def test_get_unknown_returns_404(self):
        _login(self.client)
        resp = self.client.get(self.url(99999))
        self.assertEqual(resp.status_code, 404)

    def test_patch_updates_field(self):
        _login(self.client)
        resp = self.client.patch(
            self.url(self.person.pk),
            {"display_name": "Alicia"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["display_name"], "Alicia")

    def test_patch_partial_leaves_other_fields(self):
        _login(self.client)
        self.client.patch(
            self.url(self.person.pk),
            {"colour": "#00FF00"},
            content_type="application/json",
        )
        self.person.refresh_from_db()
        self.assertEqual(self.person.display_name, "Alice")
        self.assertEqual(self.person.colour, "#00FF00")

    def test_delete_returns_204(self):
        _login(self.client)
        resp = self.client.delete(self.url(self.person.pk))
        self.assertEqual(resp.status_code, 204)

    def test_delete_then_get_returns_404(self):
        _login(self.client)
        self.client.delete(self.url(self.person.pk))
        resp = self.client.get(self.url(self.person.pk))
        self.assertEqual(resp.status_code, 404)

    def test_get_soft_deleted_returns_404(self):
        self.person.soft_delete()
        _login(self.client)
        resp = self.client.get(self.url(self.person.pk))
        self.assertEqual(resp.status_code, 404)
