"""scheduling endpoint tests — Phase 1.7.

Tests written FIRST per D10. Covers:
- Unauthenticated access rejected.
- Child accounts and guests can only view (GET).
- Users can only view.
- Managers/admins can create, update, delete standalone events.
- Synced events reject direct API writes.
- CalendarEvent ordering, detail 404.
"""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.scheduling.models import CalendarEvent
from apps.scheduling.services import create_event


def _make_user(username="admin", role=User.Role.ADMIN, is_child=False) -> User:
    user = User.objects.create_user(
        username=username, display_name=username.capitalize(), role=role, password="pass123!"
    )
    user.set_pin("1234")
    if is_child:
        user.is_child_account = True
        user.save()
    else:
        user.save()
    return user


def _login(client, username, pin="1234"):
    client.post(
        reverse("auth-pin-login"),
        {"username": username, "pin": pin},
        content_type="application/json",
    )


def _future(**kwargs):
    return (timezone.now() + timezone.timedelta(**kwargs)).isoformat()


class CalendarEventListPermissionTests(TestCase):
    """Permission matrix for GET /calendar/events/ and POST /calendar/events/."""

    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        self.manager = _make_user("manager", User.Role.MANAGER)
        self.user = _make_user("user", User.Role.USER)
        self.guest = _make_user("guest", User.Role.GUEST)
        self.child = _make_user("child", User.Role.USER, is_child=True)
        self.list_url = reverse("calendar-event-list")

    def test_unauthenticated_get_rejected(self):
        resp = self.client.get(self.list_url)
        self.assertIn(resp.status_code, [401, 403])

    def test_unauthenticated_post_rejected(self):
        resp = self.client.post(
            self.list_url,
            {"title": "x", "start_at": _future(days=1)},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [401, 403])

    def test_guest_can_get_list(self):
        _login(self.client, "guest")
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, 200)

    def test_guest_cannot_post(self):
        _login(self.client, "guest")
        resp = self.client.post(
            self.list_url,
            {"title": "x", "start_at": _future(days=1)},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [401, 403])

    def test_child_can_get_list(self):
        _login(self.client, "child")
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, 200)

    def test_child_cannot_post(self):
        _login(self.client, "child")
        resp = self.client.post(
            self.list_url,
            {"title": "x", "start_at": _future(days=1)},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [401, 403])

    def test_user_can_get_list(self):
        _login(self.client, "user")
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, 200)

    def test_user_cannot_post(self):
        _login(self.client, "user")
        resp = self.client.post(
            self.list_url,
            {"title": "x", "start_at": _future(days=1)},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [401, 403])

    def test_manager_can_post(self):
        _login(self.client, "manager")
        resp = self.client.post(
            self.list_url,
            {"title": "Staff meeting", "start_at": _future(days=1)},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_admin_can_post(self):
        _login(self.client, "admin")
        resp = self.client.post(
            self.list_url,
            {"title": "Family dinner", "start_at": _future(days=2)},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["title"], "Family dinner")


class CalendarEventCRUDTests(TestCase):
    """CRUD operations for standalone calendar events."""

    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        self.list_url = reverse("calendar-event-list")
        _login(self.client, "admin")

    def _detail_url(self, pk):
        return reverse("calendar-event-detail", kwargs={"event_id": pk})

    def test_create_event_returns_201(self):
        resp = self.client.post(
            self.list_url,
            {"title": "New event", "start_at": _future(hours=2)},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["title"], "New event")
        self.assertFalse(data["is_synced"])

    def test_list_returns_events(self):
        create_event(self.admin, title="Ev1", start_at=timezone.now())
        create_event(self.admin, title="Ev2", start_at=timezone.now())
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, 200)
        titles = [e["title"] for e in resp.json()]
        self.assertIn("Ev1", titles)
        self.assertIn("Ev2", titles)

    def test_get_detail(self):
        event = create_event(self.admin, title="Detail event", start_at=timezone.now())
        resp = self.client.get(self._detail_url(event.pk))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["title"], "Detail event")

    def test_get_missing_returns_404(self):
        resp = self.client.get(self._detail_url(99999))
        self.assertEqual(resp.status_code, 404)

    def test_patch_updates_title(self):
        event = create_event(self.admin, title="Old title", start_at=timezone.now())
        resp = self.client.patch(
            self._detail_url(event.pk),
            {"title": "New title"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["title"], "New title")

    def test_delete_returns_204_and_removes_event(self):
        event = create_event(self.admin, title="Gone", start_at=timezone.now())
        resp = self.client.delete(self._detail_url(event.pk))
        self.assertEqual(resp.status_code, 204)
        resp2 = self.client.get(self._detail_url(event.pk))
        self.assertEqual(resp2.status_code, 404)

    def test_patch_blank_title_returns_400(self):
        event = create_event(self.admin, title="Event", start_at=timezone.now())
        resp = self.client.patch(
            self._detail_url(event.pk),
            {"title": "   "},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_synced_event_patch_rejected(self):
        from apps.core.models import get_active_household
        household = get_active_household()
        event = CalendarEvent.objects.create(
            household=household,
            title="Synced",
            start_at=timezone.now(),
            created_by=self.admin,
            updated_by=self.admin,
            source_record_type="AtlasReminder",
            source_record_id=1,
        )
        resp = self.client.patch(
            self._detail_url(event.pk),
            {"title": "x"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_synced_event_delete_rejected(self):
        from apps.core.models import get_active_household
        household = get_active_household()
        event = CalendarEvent.objects.create(
            household=household,
            title="Synced",
            start_at=timezone.now(),
            created_by=self.admin,
            updated_by=self.admin,
            source_record_type="AtlasReminder",
            source_record_id=1,
        )
        resp = self.client.delete(self._detail_url(event.pk))
        self.assertEqual(resp.status_code, 400)

    def test_upcoming_filter(self):
        past = timezone.now() - timezone.timedelta(days=1)
        future = timezone.now() + timezone.timedelta(days=1)
        create_event(self.admin, title="Past", start_at=past)
        create_event(self.admin, title="Future", start_at=future)
        resp = self.client.get(self.list_url + "?upcoming=1")
        titles = [e["title"] for e in resp.json()]
        self.assertNotIn("Past", titles)
        self.assertIn("Future", titles)

    def test_date_window_filter(self):
        now = timezone.now()
        create_event(self.admin, title="InWindow", start_at=now + timezone.timedelta(days=2))
        create_event(self.admin, title="OutWindow", start_at=now + timezone.timedelta(days=20))
        start = (now).date().isoformat()
        end = (now + timezone.timedelta(days=7)).date().isoformat()
        resp = self.client.get(f"{self.list_url}?start={start}&end={end}")
        titles = [e["title"] for e in resp.json()]
        self.assertIn("InWindow", titles)
        self.assertNotIn("OutWindow", titles)

    def test_person_filter(self):
        from apps.people.services import create_person
        p1 = create_person(self.admin, display_name="Ana")
        p2 = create_person(self.admin, display_name="Bo")
        create_event(self.admin, title="Ana event", start_at=timezone.now(), assigned_to_person_id=p1.id)
        create_event(self.admin, title="Bo event", start_at=timezone.now(), assigned_to_person_id=p2.id)
        resp = self.client.get(f"{self.list_url}?person={p1.id}")
        titles = [e["title"] for e in resp.json()]
        self.assertEqual(titles, ["Ana event"])

    def test_serializer_includes_source_node_key(self):
        create_event(self.admin, title="Standalone", start_at=timezone.now())
        resp = self.client.get(self.list_url)
        event = next(e for e in resp.json() if e["title"] == "Standalone")
        self.assertIsNone(event["source_node"])
