"""Notifications tests (Milestone 2, Phase 2.15)."""
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.meridian import services as meridian
from apps.notifications import selectors, services
from apps.notifications.models import Notification
from apps.people.models import Person


def _make_user(username, role=User.Role.ADMIN, is_child=False):
    user = User.objects.create_user(
        username=username, display_name=username.capitalize(), role=role, password="pass123!"
    )
    user.set_pin("1234")
    user.is_child_account = is_child
    user.save()
    return user


def _make_person(name, *, linked_user=None):
    from apps.core.models import get_active_household
    return Person.objects.create(
        household=get_active_household(), display_name=name,
        profile_type=Person.ProfileType.CHILD, linked_user=linked_user,
    )


class NotificationServiceTests(TestCase):
    def setUp(self):
        self.user = _make_user("parent")

    def test_create_and_unread_count(self):
        services.create_notification(self.user, title="Hi", message="There")
        self.assertEqual(selectors.unread_count(self.user), 1)

    def test_notify_person_with_login(self):
        child_user = _make_user("kid", role=User.Role.USER, is_child=True)
        person = _make_person("Finn", linked_user=child_user)
        services.notify_person(person, title="T", message="M")
        self.assertEqual(selectors.unread_count(child_user), 1)

    def test_notify_person_without_login_is_noop(self):
        person = _make_person("NoLogin")
        result = services.notify_person(person, title="T", message="M")
        self.assertIsNone(result)
        self.assertEqual(Notification.objects.count(), 0)

    def test_mark_all_read(self):
        services.create_notification(self.user, title="a", message="m")
        services.create_notification(self.user, title="b", message="m")
        services.mark_all_read(self.user)
        self.assertEqual(selectors.unread_count(self.user), 0)


class NotificationWiringTests(TestCase):
    """Meridian/achievements actions surface as notifications to the right user."""

    def setUp(self):
        self.admin = _make_user("admin")
        self.child_user = _make_user("kid", role=User.Role.USER, is_child=True)
        self.person = _make_person("Finn", linked_user=self.child_user)

    def test_task_approval_notifies_child(self):
        task = meridian.create_task(self.admin, title="Tidy", points=5,
                                    assigned_to_person_id=self.person.id)
        meridian.complete_task(self.admin, task, person_id=self.person.id)
        meridian.approve_task(self.admin, task)
        notes = selectors.list_for_user(self.child_user)
        self.assertTrue(any("approved" in n.title.lower() for n in notes))

    def test_badge_earned_notifies_child(self):
        # First approved task earns the "first_task" badge → a badge notification too.
        task = meridian.create_task(self.admin, title="Tidy", points=5,
                                    assigned_to_person_id=self.person.id)
        meridian.complete_task(self.admin, task, person_id=self.person.id)
        meridian.approve_task(self.admin, task)
        self.assertTrue(
            Notification.objects.filter(recipient_user=self.child_user, title="Badge earned!").exists()
        )


class NotificationApiTests(TestCase):
    def setUp(self):
        self.user = _make_user("parent")

    def _login(self):
        self.client.post(
            reverse("auth-pin-login"),
            {"username": "parent", "pin": "1234"}, content_type="application/json",
        )

    def test_list_and_mark_read(self):
        note = services.create_notification(self.user, title="Hi", message="m")
        self._login()
        resp = self.client.get(reverse("notification-list"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["unread_count"], 1)
        resp = self.client.post(reverse("notification-read", args=[note.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(selectors.unread_count(self.user), 0)

    def test_only_see_own_notifications(self):
        other = _make_user("other", role=User.Role.USER)
        services.create_notification(other, title="theirs", message="m")
        self._login()
        resp = self.client.get(reverse("notification-list"))
        self.assertEqual(len(resp.json()["results"]), 0)
