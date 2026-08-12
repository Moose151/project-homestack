"""Education tests — Milestone 3 uni-first slice. Permission tests first (D10).

Covers:
- Permissions across roles (unauthenticated/guest/user/manager) on courses + assessments.
- CRUD for institutions, courses, assessments, class sessions.
- Calendar sync: assessment due_at and class session start_at create/update/delete a
  CalendarEvent via the scheduling helper (D7), tagged with source_node = "education".
- Visibility: a user's private course is hidden from another user; children never see it.
- Hub widgets: education_deadlines / education_classes assemble permission-filtered content.
"""
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.education.models import (
    EducationAssessment,
    EducationClassSession,
    EducationCourse,
)
from apps.education.services import (
    create_assessment,
    create_class_session,
    create_course,
    delete_assessment,
    update_assessment,
)
from apps.scheduling.models import CalendarEvent


def _make_user(username, role=User.Role.ADMIN, is_child=False) -> User:
    user = User.objects.create_user(
        username=username, display_name=username.capitalize(), role=role, password="pass123!"
    )
    user.set_pin("1234")
    if is_child:
        user.is_child_account = True
    user.save()
    return user


def _login(client, username, pin="1234"):
    client.post(
        reverse("auth-pin-login"),
        {"username": username, "pin": pin},
        content_type="application/json",
    )


def _future(hours=48):
    return timezone.now() + timezone.timedelta(hours=hours)


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

class EducationPermissionTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        self.manager = _make_user("manager", User.Role.MANAGER)
        self.user = _make_user("user", User.Role.USER)
        self.guest = _make_user("guest", User.Role.GUEST)
        self.child = _make_user("child", User.Role.USER, is_child=True)
        self.course_url = reverse("education-course-list")
        self.assessment_url = reverse("education-assessment-list")

    def test_unauthenticated_rejected(self):
        self.assertIn(self.client.get(self.course_url).status_code, [401, 403])

    def test_guest_can_view(self):
        _login(self.client, "guest")
        self.assertEqual(self.client.get(self.course_url).status_code, 200)

    def test_guest_cannot_create(self):
        _login(self.client, "guest")
        resp = self.client.post(self.course_url, {"name": "Maths"}, content_type="application/json")
        self.assertIn(resp.status_code, [401, 403])

    def test_user_can_create_course(self):
        _login(self.client, "user")
        resp = self.client.post(
            self.course_url, {"name": "Algorithms", "code": "COMP2001"}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 201)

    def test_child_cannot_create(self):
        _login(self.client, "child")
        resp = self.client.post(self.course_url, {"name": "Reading"}, content_type="application/json")
        self.assertIn(resp.status_code, [401, 403])

    def test_manager_can_delete_course(self):
        _login(self.client, "manager")
        course = create_course(self.admin, name="Physics")
        resp = self.client.delete(reverse("education-course-detail", args=[course.id]))
        self.assertEqual(resp.status_code, 204)

    def test_user_cannot_delete_course(self):
        _login(self.client, "user")
        course = create_course(self.admin, name="Physics")
        resp = self.client.delete(reverse("education-course-detail", args=[course.id]))
        self.assertIn(resp.status_code, [401, 403])


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

class EducationCrudTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        _login(self.client, "admin")

    def test_institution_crud(self):
        resp = self.client.post(
            reverse("education-institution-list"),
            {"name": "State University", "institution_type": "university"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        inst_id = resp.json()["id"]
        resp = self.client.patch(
            reverse("education-institution-detail", args=[inst_id]),
            {"location": "Main campus"}, content_type="application/json",
        )
        self.assertEqual(resp.json()["location"], "Main campus")

    def test_course_with_institution_and_student(self):
        inst = self.client.post(
            reverse("education-institution-list"), {"name": "Uni"}, content_type="application/json"
        ).json()
        resp = self.client.post(
            reverse("education-course-list"),
            {"name": "Databases", "code": "COMP3050", "institution_id": inst["id"], "teacher": "Dr Smith"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["institution_name"], "Uni")
        self.assertEqual(resp.json()["teacher"], "Dr Smith")

    def test_assessment_status_transition(self):
        course = create_course(self.admin, name="Databases")
        resp = self.client.post(
            reverse("education-assessment-list"),
            {"title": "Assignment 1", "assessment_type": "assignment", "course_id": course.id,
             "due_at": _future().isoformat()},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        aid = resp.json()["id"]
        self.assertFalse(resp.json()["is_complete"])
        resp = self.client.patch(
            reverse("education-assessment-detail", args=[aid]),
            {"status": "done"}, content_type="application/json",
        )
        self.assertTrue(resp.json()["is_complete"])

    def test_assessment_open_filter(self):
        course = create_course(self.admin, name="Databases")
        create_assessment(self.admin, title="Open one", course_id=course.id, due_at=_future())
        done = create_assessment(self.admin, title="Done one", course_id=course.id, due_at=_future())
        update_assessment(self.admin, done, status=EducationAssessment.Status.DONE)
        resp = self.client.get(reverse("education-assessment-list") + "?open=1")
        titles = [a["title"] for a in resp.json()]
        self.assertIn("Open one", titles)
        self.assertNotIn("Done one", titles)


# ---------------------------------------------------------------------------
# Calendar sync (D7)
# ---------------------------------------------------------------------------

class EducationCalendarSyncTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)

    def _events(self):
        return CalendarEvent.objects.filter(source_record_type__startswith="Education")

    def test_assessment_due_creates_event(self):
        a = create_assessment(self.admin, title="Exam", assessment_type="exam", due_at=_future())
        a.refresh_from_db()
        self.assertIsNotNone(a.calendar_event_id)
        event = CalendarEvent.objects.get(pk=a.calendar_event_id)
        self.assertEqual(event.source_node.key, "education")
        self.assertIn("Exam", event.title)

    def test_assessment_without_due_creates_no_event(self):
        a = create_assessment(self.admin, title="No date")
        self.assertIsNone(a.calendar_event_id)
        self.assertEqual(self._events().count(), 0)

    def test_updating_due_updates_event(self):
        a = create_assessment(self.admin, title="Quiz", due_at=_future(24))
        new_due = _future(72)
        update_assessment(self.admin, a, due_at=new_due)
        event = CalendarEvent.objects.get(pk=a.calendar_event_id)
        self.assertEqual(event.start_at, new_due)

    def test_deleting_assessment_deletes_event(self):
        a = create_assessment(self.admin, title="Quiz", due_at=_future())
        event_id = a.calendar_event_id
        delete_assessment(self.admin, a)
        self.assertFalse(CalendarEvent.objects.filter(pk=event_id).exists())

    def test_class_session_creates_recurring_event(self):
        s = create_class_session(
            self.admin, title="Lecture", start_at=_future(2), end_at=_future(3),
            recurrence_rule="FREQ=WEEKLY;BYDAY=MO",
        )
        s.refresh_from_db()
        self.assertIsNotNone(s.calendar_event_id)
        event = CalendarEvent.objects.get(pk=s.calendar_event_id)
        self.assertEqual(event.recurrence_rule, "FREQ=WEEKLY;BYDAY=MO")
        self.assertEqual(event.source_node.key, "education")


# ---------------------------------------------------------------------------
# Repeating timetable classes
# ---------------------------------------------------------------------------

class ClassSeriesTests(TestCase):
    """A repeating class must land on the calendar for every week of term, not just the first.

    Ticking "repeats weekly" used to write FREQ=WEEKLY onto one row. Nothing expands a
    recurrence rule on read — the calendar lists real CalendarEvent rows — so exactly one class
    ever appeared.
    """

    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        _login(self.client, "admin")
        household = self.admin.household
        household.timezone = "Australia/Sydney"
        household.save(update_fields=["timezone"])

    def _create(self, **payload):
        body = {
            "title": "Lecture",
            "start_at": "2026-03-02T09:00:00Z",
            "duration_minutes": 60,
        }
        body.update(payload)
        return self.client.post(
            reverse("education-class-list"), body, content_type="application/json",
        )

    def _events(self):
        return CalendarEvent.objects.filter(source_record_type__startswith="Education")

    def test_a_weekly_class_creates_one_session_per_week_until_the_last_date(self):
        response = self._create(repeat="weekly", repeat_until="2026-03-30")
        self.assertEqual(response.status_code, 201, response.json())
        created = response.json()
        # 2, 9, 16, 23 and 30 March — the last date is inclusive.
        self.assertEqual(len(created), 5)
        self.assertEqual(self._events().count(), 5)
        self.assertEqual(
            [row["start_at"][:10] for row in created],
            ["2026-03-02", "2026-03-09", "2026-03-16", "2026-03-23", "2026-03-30"],
        )

    def test_every_occurrence_keeps_the_duration_and_shares_a_series_key(self):
        created = self._create(repeat="fortnightly", repeat_until="2026-03-30").json()
        self.assertEqual(len(created), 3)  # 2, 16, 30 March
        keys = {row["series_key"] for row in created}
        self.assertEqual(len(keys), 1)
        self.assertNotIn(None, keys)
        for row in created:
            session = EducationClassSession.objects.get(pk=row["id"])
            self.assertEqual((session.end_at - session.start_at).total_seconds(), 3600)

    def test_a_class_without_a_repeat_is_still_a_single_session(self):
        created = self._create().json()
        self.assertEqual(len(created), 1)
        self.assertIsNone(created[0]["series_key"])
        self.assertEqual(self._events().count(), 1)

    def test_repeat_without_a_last_date_is_rejected(self):
        response = self._create(repeat="weekly")
        self.assertEqual(response.status_code, 400)
        self.assertIn("repeat_until", response.json())
        self.assertEqual(EducationClassSession.objects.count(), 0)

    def test_a_last_date_before_the_first_class_is_rejected(self):
        response = self._create(repeat="weekly", repeat_until="2026-02-01")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(EducationClassSession.objects.count(), 0)

    def test_an_absurd_range_is_refused_rather_than_creating_hundreds_of_classes(self):
        response = self._create(repeat="weekly", repeat_until="2030-03-30")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(EducationClassSession.objects.count(), 0)

    def test_the_local_class_time_survives_a_daylight_saving_change(self):
        # Sydney leaves daylight saving on 2026-04-05. A 09:00 class must stay 09:00 local on
        # both sides of it, which stepping in UTC would not do.
        from zoneinfo import ZoneInfo

        created = self._create(
            start_at="2026-03-29T09:00:00+11:00", repeat="weekly", repeat_until="2026-04-12",
        ).json()
        sydney = ZoneInfo("Australia/Sydney")
        local_hours = {
            EducationClassSession.objects.get(pk=row["id"]).start_at.astimezone(sydney).hour
            for row in created
        }
        self.assertEqual(local_hours, {9})

    def test_deleting_one_class_leaves_the_rest_of_the_series(self):
        created = self._create(repeat="weekly", repeat_until="2026-03-16").json()
        self.client.delete(reverse("education-class-detail", args=[created[0]["id"]]))
        self.assertEqual(EducationClassSession.objects.count(), 2)
        self.assertEqual(self._events().count(), 2)

    def test_deleting_the_series_removes_every_class_and_its_events(self):
        created = self._create(repeat="weekly", repeat_until="2026-03-16").json()
        response = self.client.delete(
            f"{reverse('education-class-detail', args=[created[0]['id']])}?series=1"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["deleted"], 3)
        self.assertEqual(EducationClassSession.objects.count(), 0)
        self.assertEqual(self._events().count(), 0)


# ---------------------------------------------------------------------------
# Visibility (D10)
# ---------------------------------------------------------------------------

class EducationVisibilityTests(TestCase):
    def setUp(self):
        self.owner = _make_user("owner", User.Role.USER)
        self.other = _make_user("other", User.Role.USER)
        self.child = _make_user("child", User.Role.USER, is_child=True)
        self.private_course = create_course(
            self.owner, name="Private Uni Course", visibility="private",
        )

    def test_owner_sees_own_private_course(self):
        from apps.education.selectors import list_courses
        names = [c.name for c in list_courses(self.owner)]
        self.assertIn("Private Uni Course", names)

    def test_other_user_cannot_see_private_course(self):
        from apps.education.selectors import list_courses
        names = [c.name for c in list_courses(self.other)]
        self.assertNotIn("Private Uni Course", names)

    def test_child_cannot_see_private_course(self):
        from apps.education.selectors import list_courses
        names = [c.name for c in list_courses(self.child)]
        self.assertNotIn("Private Uni Course", names)


# ---------------------------------------------------------------------------
# Hub widgets (Node Spec 8)
# ---------------------------------------------------------------------------

class EducationHubWidgetTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)

    def test_deadlines_widget_lists_open_upcoming(self):
        from apps.hub.services import _education_widget_content
        create_assessment(self.admin, title="Due soon", due_at=_future())
        content = _education_widget_content("education_deadlines", self.admin)
        self.assertTrue(any(a["title"] == "Due soon" for a in content))

    def test_classes_widget_lists_sessions(self):
        from apps.hub.services import _education_widget_content
        create_class_session(self.admin, title="Lecture", start_at=_future())
        content = _education_widget_content("education_classes", self.admin)
        self.assertEqual(len(content), 1)


# ---------------------------------------------------------------------------
# Assessment notes + files (D11 — no per-row ACL, visibility+sensitivity only)
# ---------------------------------------------------------------------------

class AssessmentNotesTests(TestCase):
    def setUp(self):
        self.user = _make_user("noteuser", User.Role.USER)
        self.assessment = create_assessment(self.user, title="Essay")
        self.client.force_login(self.user)

    def test_list_notes_empty(self):
        url = f"/api/v1/education/assessments/{self.assessment.id}/notes/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [])

    def test_create_and_list_note(self):
        url = f"/api/v1/education/assessments/{self.assessment.id}/notes/"
        res = self.client.post(url, {"body": "Check rubric page 3"}, content_type="application/json")
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["body"], "Check rubric page 3")
        self.assertEqual(data["assessment_id"], self.assessment.id)

        res2 = self.client.get(url)
        self.assertEqual(len(res2.json()), 1)

    def test_update_note(self):
        from apps.education.services import create_assessment_note
        note = create_assessment_note(self.user, self.assessment, "Original text")
        url = f"/api/v1/education/assessments/{self.assessment.id}/notes/{note.id}/"
        res = self.client.patch(url, {"body": "Updated text"}, content_type="application/json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["body"], "Updated text")

    def test_delete_note(self):
        from apps.education.services import create_assessment_note
        note = create_assessment_note(self.user, self.assessment, "Temporary note")
        url = f"/api/v1/education/assessments/{self.assessment.id}/notes/{note.id}/"
        res = self.client.delete(url)
        self.assertEqual(res.status_code, 204)
        res2 = self.client.get(f"/api/v1/education/assessments/{self.assessment.id}/notes/")
        self.assertEqual(res2.json(), [])

    def test_blank_body_rejected(self):
        url = f"/api/v1/education/assessments/{self.assessment.id}/notes/"
        res = self.client.post(url, {"body": "  "}, content_type="application/json")
        self.assertEqual(res.status_code, 400)

    def test_unauthenticated_cannot_access_notes(self):
        self.client.logout()
        url = f"/api/v1/education/assessments/{self.assessment.id}/notes/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, 403)


class AssessmentFilesSecurityTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp(prefix="homestack-education-files-")
        self.media_override = override_settings(MEDIA_ROOT=self.media_root)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, True)
        self.owner = _make_user("fileowner", User.Role.USER)
        self.other = _make_user("fileother", User.Role.USER)
        self.assessment = create_assessment(
            self.owner,
            title="Private brief",
            visibility="private",
        )
        self.list_url = reverse(
            "education-assessment-file-list",
            args=[self.assessment.id],
        )

    def _upload(self):
        self.client.force_login(self.owner)
        return self.client.post(
            self.list_url,
            {"file": SimpleUploadedFile("brief.pdf", b"assignment brief", content_type="application/pdf")},
        )

    def test_file_url_uses_permission_checked_download_endpoint(self):
        response = self._upload()

        self.assertEqual(response.status_code, 201)
        file_url = response.json()["file_url"]
        self.assertIn("/api/v1/education/assessments/", file_url)
        self.assertTrue(file_url.endswith("/download/"))
        self.assertNotIn("/media/", file_url)

    def test_owner_can_download_assessment_file(self):
        uploaded = self._upload().json()

        response = self.client.get(uploaded["file_url"])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"assignment brief")

    def test_other_user_cannot_list_or_download_private_assessment_files(self):
        uploaded = self._upload().json()
        self.client.force_login(self.other)

        self.assertEqual(self.client.get(self.list_url).status_code, 404)
        self.assertEqual(self.client.get(uploaded["file_url"]).status_code, 404)


# ---------------------------------------------------------------------------
# Education events (excursions, school events, term dates, milestones)
# ---------------------------------------------------------------------------

class EducationEventTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        _login(self.client, "admin")
        self.list_url = reverse("education-event-list")

    def test_create_event_syncs_calendar(self):
        from apps.education.services import create_event
        e = create_event(
            self.admin, title="Field trip", event_type="excursion", start_at=_future(),
        )
        e.refresh_from_db()
        self.assertIsNotNone(e.calendar_event_id)
        event = CalendarEvent.objects.get(pk=e.calendar_event_id)
        self.assertEqual(event.source_node.key, "education")
        self.assertIn("Field trip", event.title)

    def test_update_and_delete_event_syncs_calendar(self):
        from apps.education.services import create_event, delete_event, update_event
        e = create_event(self.admin, title="Open day", start_at=_future(24))
        new_start = _future(72)
        update_event(self.admin, e, start_at=new_start)
        self.assertEqual(CalendarEvent.objects.get(pk=e.calendar_event_id).start_at, new_start)
        event_id = e.calendar_event_id
        delete_event(self.admin, e)
        self.assertFalse(CalendarEvent.objects.filter(pk=event_id).exists())

    def test_event_crud_via_api(self):
        res = self.client.post(
            self.list_url,
            {"title": "Term starts", "event_type": "term_start", "start_at": _future().isoformat()},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        event_id = res.json()["id"]

        res = self.client.get(self.list_url)
        self.assertTrue(any(e["title"] == "Term starts" for e in res.json()))

        res = self.client.patch(
            reverse("education-event-detail", args=[event_id]),
            {"location": "Main hall"}, content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["location"], "Main hall")

        res = self.client.delete(reverse("education-event-detail", args=[event_id]))
        self.assertEqual(res.status_code, 204)

    def test_start_at_required(self):
        res = self.client.post(
            self.list_url, {"title": "No date"}, content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)

    def test_events_hub_widget_lists_upcoming(self):
        from apps.education.services import create_event
        from apps.hub.services import _education_widget_content
        create_event(self.admin, title="Sports day", start_at=_future())
        create_event(self.admin, title="Last term", start_at=_future(-48))  # past → excluded
        content = _education_widget_content("education_events", self.admin)
        titles = [e["title"] for e in content]
        self.assertIn("Sports day", titles)
        self.assertNotIn("Last term", titles)

    def test_search_includes_events(self):
        from apps.education.services import create_event
        create_event(self.admin, title="Graduation ceremony", start_at=_future())
        res = self.client.get(reverse("education-search"), {"q": "Graduation"})
        self.assertEqual(res.status_code, 200)
        titles = [e["title"] for e in res.json()["events"]]
        self.assertIn("Graduation ceremony", titles)

    def test_assigned_person_notified_on_create(self):
        from apps.education.services import create_event
        from apps.notifications.models import Notification
        from apps.people.models import Person
        student_user = _make_user("student", User.Role.USER)
        person = Person.objects.create(
            household=self.admin.household, display_name="Student",
            linked_user=student_user, created_by=self.admin, updated_by=self.admin,
        )
        create_event(
            self.admin, title="Excursion", event_type="excursion",
            start_at=_future(), assigned_to_people=[person],
        )
        self.assertTrue(
            Notification.objects.filter(recipient_user=student_user, source_node="education").exists()
        )
