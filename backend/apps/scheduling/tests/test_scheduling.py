"""scheduling endpoint tests — Phase 1.7.

Tests written FIRST per D10. Covers:
- Unauthenticated access rejected.
- Child accounts and guests can only view (GET).
- Users can only view.
- Managers/admins can create, update, delete standalone events.
- Synced events reject direct API writes.
- CalendarEvent ordering, detail 404.
"""
from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.scheduling.models import CalendarEvent, RotatingSchedule, RotatingScheduleException
from apps.people.services import create_person
from apps.scheduling.selectors import list_events
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
        create_event(self.admin, title="Ana event", start_at=timezone.now(), assigned_to_people=[p1])
        create_event(self.admin, title="Bo event", start_at=timezone.now(), assigned_to_people=[p2])
        resp = self.client.get(f"{self.list_url}?person={p1.id}")
        titles = [e["title"] for e in resp.json()]
        self.assertEqual(titles, ["Ana event"])

    def test_serializer_includes_source_node_key(self):
        create_event(self.admin, title="Standalone", start_at=timezone.now())
        resp = self.client.get(self.list_url)
        event = next(e for e in resp.json() if e["title"] == "Standalone")
        self.assertIsNone(event["source_node"])

    def test_atlas_synced_event_exposes_source_node_and_respects_visibility(self):
        from apps.atlas.models import Visibility as AtlasVisibility
        from apps.atlas.services import create_reminder
        reminder = create_reminder(
            self.admin, title="Private reminder", due_at=timezone.now(),
            visibility=AtlasVisibility.PRIVATE,
        )
        self.assertIsNotNone(reminder.calendar_event_id)

        resp = self.client.get(self.list_url)
        event = next(e for e in resp.json() if e["title"] == "Private reminder")
        self.assertEqual(event["source_node"], "atlas")

        child = _make_user("child_private", User.Role.USER, is_child=True)
        _login(self.client, "child_private")
        child_resp = self.client.get(self.list_url)
        self.assertNotIn("Private reminder", [e["title"] for e in child_resp.json()])

    def test_meridian_deadlines_render_for_allowed_roles_only(self):
        from apps.meridian import services as meridian_services
        from apps.meridian.models import Visibility as MeridianVisibility
        task = meridian_services.create_task(
            self.admin, title="Private Meridian deadline", points=5,
            due_at=timezone.now(), visibility=MeridianVisibility.PRIVATE,
        )
        self.assertIsNotNone(task.calendar_event_id)

        admin_resp = self.client.get(self.list_url)
        event = next(e for e in admin_resp.json() if e["title"] == "Private Meridian deadline")
        self.assertEqual(event["source_node"], "meridian")

        child = _make_user("child_meridian", User.Role.USER, is_child=True)
        _login(self.client, "child_meridian")
        child_resp = self.client.get(self.list_url)
        self.assertNotIn("Private Meridian deadline", [e["title"] for e in child_resp.json()])


class RotatingScheduleTests(TestCase):
    """One canonical cycle can be forecast indefinitely and changed per date."""

    pattern = "PPSSPPPSSPPSSS"  # 2 on, 2 off, 3 on, 2 off, 2 on, 3 off

    def setUp(self):
        self.admin = _make_user("rotation_admin", User.Role.ADMIN)
        self.guest = _make_user("rotation_guest", User.Role.GUEST)
        self.list_url = reverse("rotating-schedule-list")
        self.occurrences_url = reverse("rotating-schedule-occurrence-list")

    def _create(self, **overrides):
        payload = {
            "title": "Kids",
            "primary_label": "With us",
            "secondary_label": "With Dad",
            "anchor_date": "2026-08-03",
            "cycle_pattern": self.pattern,
            **overrides,
        }
        return self.client.post(self.list_url, payload, content_type="application/json")

    def test_unauthenticated_access_is_rejected(self):
        self.assertIn(self.client.get(self.list_url).status_code, [401, 403])
        self.assertIn(self.client.get(self.occurrences_url).status_code, [401, 403])

    def test_guest_can_view_but_cannot_create(self):
        _login(self.client, "rotation_guest")
        self.assertEqual(self.client.get(self.list_url).status_code, 200)
        self.assertIn(self._create().status_code, [401, 403])

    def test_guest_cannot_change_or_restore_an_exception(self):
        from apps.scheduling.services import create_rotating_schedule

        schedule = create_rotating_schedule(
            self.admin,
            title="Kids",
            primary_label="With us",
            secondary_label="Other home",
            anchor_date=date(2026, 8, 3),
            cycle_pattern=self.pattern,
        )
        url = reverse(
            "rotating-schedule-exception-detail",
            kwargs={"schedule_id": schedule.id, "date": "2026-08-05"},
        )
        _login(self.client, "rotation_guest")
        self.assertIn(
            self.client.put(url, {"state": "primary"}, content_type="application/json").status_code,
            [401, 403],
        )
        self.assertIn(self.client.delete(url).status_code, [401, 403])

    def test_create_and_expand_exact_fourteen_day_pattern(self):
        _login(self.client, "rotation_admin")
        response = self._create()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["cycle_length"], 14)
        self.assertEqual(CalendarEvent.objects.count(), 0)

        response = self.client.get(
            f"{self.occurrences_url}?start=2026-08-03&end=2026-08-17"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [row["state"] for row in response.json()],
            ["primary" if value == "P" else "secondary" for value in self.pattern],
        )
        self.assertTrue(all(not row["is_override"] for row in response.json()))

    def test_pattern_forecasts_far_into_the_future(self):
        _login(self.client, "rotation_admin")
        self._create()
        # 1400 days is exactly 100 cycles after the anchor.
        response = self.client.get(
            f"{self.occurrences_url}?start=2030-06-03&end=2030-06-04"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["state"], "primary")

    def test_date_exception_can_swap_state_then_restore_pattern(self):
        _login(self.client, "rotation_admin")
        schedule_id = self._create().json()["id"]
        exception_url = reverse(
            "rotating-schedule-exception-detail",
            kwargs={"schedule_id": schedule_id, "date": "2026-08-05"},
        )
        response = self.client.put(
            exception_url,
            {"state": "primary", "note": "Agreed swap"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RotatingScheduleException.objects.count(), 1)

        occurrence = self.client.get(
            f"{self.occurrences_url}?start=2026-08-05&end=2026-08-06"
        ).json()[0]
        self.assertEqual(occurrence["state"], "primary")
        self.assertTrue(occurrence["is_override"])
        self.assertEqual(occurrence["note"], "Agreed swap")

        self.assertEqual(self.client.delete(exception_url).status_code, 204)
        restored = self.client.get(
            f"{self.occurrences_url}?start=2026-08-05&end=2026-08-06"
        ).json()[0]
        self.assertEqual(restored["state"], "secondary")
        self.assertFalse(restored["is_override"])

    def test_soft_deleted_exception_is_reused_when_date_is_changed_again(self):
        _login(self.client, "rotation_admin")
        schedule_id = self._create().json()["id"]
        url = reverse(
            "rotating-schedule-exception-detail",
            kwargs={"schedule_id": schedule_id, "date": "2026-08-05"},
        )
        self.client.put(url, {"state": "primary"}, content_type="application/json")
        self.client.delete(url)
        response = self.client.put(
            url, {"state": "primary", "note": "Second swap"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RotatingScheduleException.all_objects.count(), 1)
        self.assertEqual(response.json()["note"], "Second swap")

    def test_invalid_pattern_and_invalid_window_are_rejected(self):
        _login(self.client, "rotation_admin")
        self.assertEqual(self._create(cycle_pattern="PPXSS").status_code, 400)
        self._create()
        self.assertEqual(
            self.client.get(f"{self.occurrences_url}?start=bad&end=2026-08-10").status_code,
            400,
        )
        self.assertEqual(
            self.client.get(
                f"{self.occurrences_url}?start=2026-08-10&end=2026-08-03"
            ).status_code,
            400,
        )

    def test_people_are_attached_once_to_schedule_not_copied_to_days(self):
        from apps.people.services import create_person

        child = create_person(self.admin, display_name="Child", profile_type="child")
        _login(self.client, "rotation_admin")
        response = self._create(person_ids=[child.id])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["people"][0]["display_name"], "Child")
        schedule = RotatingSchedule.objects.get(pk=response.json()["id"])
        self.assertEqual(list(schedule.people.values_list("id", flat=True)), [child.id])

    def test_schedule_can_be_edited_and_soft_deleted(self):
        _login(self.client, "rotation_admin")
        schedule_id = self._create().json()["id"]
        url = reverse("rotating-schedule-detail", kwargs={"schedule_id": schedule_id})
        response = self.client.patch(
            url,
            {"secondary_label": "With other carer", "cycle_pattern": "PS"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["secondary_label"], "With other carer")
        self.assertEqual(response.json()["cycle_length"], 2)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertFalse(RotatingSchedule.objects.filter(pk=schedule_id).exists())
        self.assertTrue(RotatingSchedule.all_objects.filter(pk=schedule_id).exists())

    def test_private_schedule_is_hidden_from_child_account(self):
        _login(self.client, "rotation_admin")
        self._create(title="Private rotation", visibility="private")
        child = _make_user("rotation_child", User.Role.USER, is_child=True)
        _login(self.client, child.username)
        self.assertEqual(self.client.get(self.list_url).json(), [])
        self.assertEqual(
            self.client.get(
                f"{self.occurrences_url}?start=2026-08-03&end=2026-08-04"
            ).json(),
            [],
        )


class MultiPersonAssignmentTests(TestCase):
    """Assignment is a set, not one person (owner request, 2026-08-09).

    Empty means the whole household; one or more people means each of them. The filter must
    match an event if the person is *any* of its assignees, and must not return it twice.
    """

    def setUp(self):
        self.admin = _make_user("assign_admin", User.Role.ADMIN)
        self.client.force_login(self.admin)
        self.ana = create_person(self.admin, display_name="Ana")
        self.bo = create_person(self.admin, display_name="Bo")

    def test_event_can_be_assigned_to_several_people(self):
        event = create_event(
            self.admin, title="School run", start_at=timezone.now(),
            assigned_to_people=[self.ana, self.bo],
        )
        self.assertEqual(
            set(event.assigned_to_people.values_list("id", flat=True)),
            {self.ana.id, self.bo.id},
        )

    def test_filter_matches_any_assignee_exactly_once(self):
        create_event(
            self.admin, title="School run", start_at=timezone.now(),
            assigned_to_people=[self.ana, self.bo],
        )
        for person in (self.ana, self.bo):
            events = list_events(self.admin, person=person.id)
            self.assertEqual([e.title for e in events], ["School run"], person.display_name)

    def test_no_assignees_means_the_whole_household(self):
        create_event(self.admin, title="Bin day", start_at=timezone.now())
        self.assertEqual(list_events(self.admin, person=self.ana.id), [])
        self.assertIn("Bin day", [e.title for e in list_events(self.admin)])

    def test_api_round_trips_the_assignee_list(self):
        response = self.client.post(
            reverse("calendar-event-list"),
            {
                "title": "Dentist",
                "start_at": timezone.now().isoformat(),
                "assigned_to_person_ids": [self.ana.id, self.bo.id],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            sorted(response.json()["assigned_to_person_ids"]),
            sorted([self.ana.id, self.bo.id]),
        )

    def test_partial_update_without_assignees_leaves_them_alone(self):
        event = create_event(
            self.admin, title="School run", start_at=timezone.now(),
            assigned_to_people=[self.ana],
        )
        self.client.patch(
            reverse("calendar-event-detail", args=[event.id]),
            {"title": "School pickup"},
            content_type="application/json",
        )
        event.refresh_from_db()
        self.assertEqual(event.title, "School pickup")
        self.assertEqual(list(event.assigned_to_people.values_list("id", flat=True)), [self.ana.id])

    def test_assignees_can_be_cleared_back_to_the_household(self):
        event = create_event(
            self.admin, title="School run", start_at=timezone.now(),
            assigned_to_people=[self.ana, self.bo],
        )
        self.client.patch(
            reverse("calendar-event-detail", args=[event.id]),
            {"assigned_to_person_ids": []},
            content_type="application/json",
        )
        event.refresh_from_db()
        self.assertEqual(event.assigned_to_people.count(), 0)
