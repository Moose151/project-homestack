"""Meridian tests — Milestone 2 (D13, D14). Permission-first per D10.

Covers:
- Permissions across roles, including the narrow child-safe carve-out (complete/request
  allowed for children; create/edit/delete/approve still blocked).
- Task CRUD and the lifecycle: complete → approve (awards points) / reject (no points).
- Rewards: request → approve (deducts points), insufficient-points rejection.
- Calendar sync for dated tasks via the scheduling helper (D7).
- Points summary, search, visibility, and the kiosk endpoint.
"""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.meridian import selectors, services
from apps.meridian.models import (
    MeridianPointsEntry,
    MeridianReward,
    MeridianRewardRequest,
    MeridianTask,
)
from apps.people.models import Person
from apps.scheduling.models import CalendarEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(username, role=User.Role.ADMIN, is_child=False) -> User:
    user = User.objects.create_user(
        username=username, display_name=username.capitalize(), role=role, password="pass123!"
    )
    user.set_pin("1234")
    user.is_child_account = is_child
    user.save()
    return user


def _make_person(name, *, linked_user=None, profile_type=Person.ProfileType.CHILD) -> Person:
    from apps.core.models import get_active_household
    return Person.objects.create(
        household=get_active_household(),
        display_name=name,
        profile_type=profile_type,
        linked_user=linked_user,
    )


def _login(client, username, pin="1234"):
    client.post(
        reverse("auth-pin-login"),
        {"username": username, "pin": pin},
        content_type="application/json",
    )


def _future(hours=24):
    return timezone.now() + timezone.timedelta(hours=hours)


# ---------------------------------------------------------------------------
# Permission tests (D10)
# ---------------------------------------------------------------------------

class TaskPermissionTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", role=User.Role.ADMIN)
        self.manager = _make_user("manager", role=User.Role.MANAGER)
        self.user = _make_user("parentuser", role=User.Role.USER)
        self.child = _make_user("kid", role=User.Role.USER, is_child=True)
        self.list_url = reverse("meridian-task-list")

    def test_unauthenticated_denied(self):
        self.assertEqual(self.client.get(self.list_url).status_code, 403)

    def test_all_roles_can_view(self):
        for name in ("admin", "manager", "parentuser", "kid"):
            _login(self.client, name)
            self.assertEqual(self.client.get(self.list_url).status_code, 200)

    def test_user_cannot_create_task(self):
        _login(self.client, "parentuser")
        resp = self.client.post(
            self.list_url, {"title": "Dishes", "points": 5}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_create_task(self):
        _login(self.client, "admin")
        resp = self.client.post(
            self.list_url, {"title": "Dishes", "points": 5}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 201)

    def test_child_cannot_create_or_approve(self):
        task = services.create_task(self.admin, title="Bins", points=3)
        _login(self.client, "kid")
        self.assertEqual(
            self.client.post(self.list_url, {"title": "x"}, content_type="application/json").status_code,
            403,
        )
        self.assertEqual(
            self.client.post(reverse("meridian-task-approve", args=[task.id])).status_code, 403
        )


class ChildSafeActionTests(TestCase):
    """The narrow carve-out: children may complete tasks and request rewards only."""

    def setUp(self):
        self.admin = _make_user("admin", role=User.Role.ADMIN)
        self.child_user = _make_user("kid", role=User.Role.USER, is_child=True)
        self.child_person = _make_person("Finn", linked_user=self.child_user)

    def test_child_can_complete_own_task(self):
        task = services.create_task(
            self.admin, title="Tidy room", points=10, assigned_to_person_id=self.child_person.id
        )
        _login(self.client, "kid")
        resp = self.client.post(reverse("meridian-task-complete", args=[task.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "pending")
        task.refresh_from_db()
        self.assertEqual(task.completed_by_person_id, self.child_person.id)

    def test_child_complete_awards_no_points_until_approved(self):
        task = services.create_task(
            self.admin, title="Tidy room", points=10, assigned_to_person_id=self.child_person.id
        )
        _login(self.client, "kid")
        self.client.post(reverse("meridian-task-complete", args=[task.id]))
        self.assertEqual(services.get_points_balance(self.child_person.id), 0)

    def test_child_can_request_reward_with_enough_points(self):
        services.adjust_points(self.admin, person_id=self.child_person.id, points=50)
        reward = services.create_reward(self.admin, name="Movie night", cost_points=20)
        _login(self.client, "kid")
        resp = self.client.post(reverse("meridian-reward-request", args=[reward.id]))
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(MeridianRewardRequest.objects.count(), 1)

    def test_child_cannot_request_reward_without_points(self):
        reward = services.create_reward(self.admin, name="Movie night", cost_points=20)
        _login(self.client, "kid")
        resp = self.client.post(reverse("meridian-reward-request", args=[reward.id]))
        self.assertEqual(resp.status_code, 400)

    def test_child_cannot_approve_reward_request(self):
        services.adjust_points(self.admin, person_id=self.child_person.id, points=50)
        reward = services.create_reward(self.admin, name="Movie night", cost_points=20)
        req = services.request_reward(self.admin, reward, person_id=self.child_person.id)
        _login(self.client, "kid")
        resp = self.client.post(reverse("meridian-reward-request-approve", args=[req.id]))
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# Task lifecycle + points
# ---------------------------------------------------------------------------

class TaskLifecycleTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", role=User.Role.ADMIN)
        self.person = _make_person("Finn")

    def test_complete_then_approve_awards_points(self):
        task = services.create_task(
            self.admin, title="Dishes", points=15, assigned_to_person_id=self.person.id
        )
        services.complete_task(self.admin, task, person_id=self.person.id)
        self.assertEqual(task.status, MeridianTask.Status.PENDING)
        services.approve_task(self.admin, task)
        task.refresh_from_db()
        self.assertEqual(task.status, MeridianTask.Status.APPROVED)
        self.assertEqual(services.get_points_balance(self.person.id), 15)
        self.assertEqual(MeridianPointsEntry.objects.filter(source_task=task).count(), 1)

    def test_reject_returns_task_available_and_no_points(self):
        task = services.create_task(
            self.admin, title="Dishes", points=15, assigned_to_person_id=self.person.id
        )
        services.complete_task(self.admin, task, person_id=self.person.id)
        services.reject_task(self.admin, task, reason="Not actually done")
        task.refresh_from_db()
        self.assertEqual(task.status, MeridianTask.Status.AVAILABLE)
        self.assertEqual(task.rejection_reason, "Not actually done")
        self.assertEqual(services.get_points_balance(self.person.id), 0)

    def test_approve_only_from_pending(self):
        task = services.create_task(self.admin, title="Dishes", points=15)
        with self.assertRaises(services.MeridianError):
            services.approve_task(self.admin, task)

    def test_double_approve_does_not_double_award(self):
        task = services.create_task(
            self.admin, title="Dishes", points=15, assigned_to_person_id=self.person.id
        )
        services.complete_task(self.admin, task, person_id=self.person.id)
        services.approve_task(self.admin, task)
        with self.assertRaises(services.MeridianError):
            services.approve_task(self.admin, task)
        self.assertEqual(services.get_points_balance(self.person.id), 15)

    def test_hot_task_awards_bonus_points(self):
        task = services.create_task(
            self.admin, title="Big clean", points=10, is_hot=True, hot_bonus_points=5,
            assigned_to_person_id=self.person.id,
        )
        self.assertEqual(task.award_value, 15)
        services.complete_task(self.admin, task, person_id=self.person.id)
        services.approve_task(self.admin, task)
        self.assertEqual(services.get_points_balance(self.person.id), 15)

    def test_hide_after_approval_deactivates_task(self):
        task = services.create_task(
            self.admin, title="One-off", points=5,
            completion_behavior=MeridianTask.CompletionBehavior.HIDE_AFTER_APPROVAL,
            assigned_to_person_id=self.person.id,
        )
        services.complete_task(self.admin, task, person_id=self.person.id)
        services.approve_task(self.admin, task)
        task.refresh_from_db()
        self.assertFalse(task.is_active)

    def test_archived_task_hidden_from_default_list(self):
        services.create_task(self.admin, title="Old chore", points=5)
        archived = services.create_task(self.admin, title="Retired chore", points=5)
        services.update_task(self.admin, archived, is_archived=True)
        titles = {t.title for t in selectors.list_tasks(self.admin)}
        self.assertIn("Old chore", titles)
        self.assertNotIn("Retired chore", titles)

    def test_approve_via_api(self):
        task = services.create_task(
            self.admin, title="Dishes", points=8, assigned_to_person_id=self.person.id
        )
        services.complete_task(self.admin, task, person_id=self.person.id)
        _login(self.client, "admin")
        resp = self.client.post(reverse("meridian-task-approve", args=[task.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(services.get_points_balance(self.person.id), 8)


# ---------------------------------------------------------------------------
# Rewards
# ---------------------------------------------------------------------------

class RewardTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", role=User.Role.ADMIN)
        self.person = _make_person("Finn")

    def test_request_then_approve_deducts_points(self):
        services.adjust_points(self.admin, person_id=self.person.id, points=100)
        reward = services.create_reward(self.admin, name="Ice cream", cost_points=30)
        req = services.request_reward(self.admin, reward, person_id=self.person.id)
        services.approve_reward_request(self.admin, req)
        req.refresh_from_db()
        self.assertEqual(req.status, MeridianRewardRequest.Status.APPROVED)
        self.assertEqual(req.points_spent, 30)
        self.assertEqual(services.get_points_balance(self.person.id), 70)

    def test_request_rejected_when_insufficient(self):
        reward = services.create_reward(self.admin, name="Ice cream", cost_points=30)
        with self.assertRaises(services.MeridianError):
            services.request_reward(self.admin, reward, person_id=self.person.id)

    def test_request_reserves_points_immediately(self):
        services.adjust_points(self.admin, person_id=self.person.id, points=100)
        reward = services.create_reward(self.admin, name="Ice cream", cost_points=30)
        services.request_reward(self.admin, reward, person_id=self.person.id)
        # Points are held (reserved) the moment the request is made.
        self.assertEqual(services.get_points_balance(self.person.id), 70)

    def test_reject_request_refunds_points(self):
        services.adjust_points(self.admin, person_id=self.person.id, points=100)
        reward = services.create_reward(self.admin, name="Ice cream", cost_points=30)
        req = services.request_reward(self.admin, reward, person_id=self.person.id)
        services.reject_reward_request(self.admin, req, reason="Maybe next week")
        self.assertEqual(services.get_points_balance(self.person.id), 100)

    def test_cancel_request_refunds_points_once(self):
        services.adjust_points(self.admin, person_id=self.person.id, points=100)
        reward = services.create_reward(self.admin, name="Ice cream", cost_points=30)
        req = services.request_reward(self.admin, reward, person_id=self.person.id)
        services.cancel_reward_request(self.admin, req)
        self.assertEqual(services.get_points_balance(self.person.id), 100)
        # Re-cancelling a non-pending request is rejected; balance stays correct.
        with self.assertRaises(services.MeridianError):
            services.cancel_reward_request(self.admin, req)
        self.assertEqual(services.get_points_balance(self.person.id), 100)

    def test_cannot_reserve_points_already_held(self):
        services.adjust_points(self.admin, person_id=self.person.id, points=40)
        reward = services.create_reward(self.admin, name="Toy", cost_points=30)
        services.request_reward(self.admin, reward, person_id=self.person.id)  # reserves 30
        # Only 10 left — a second request cannot be made.
        with self.assertRaises(services.MeridianError):
            services.request_reward(self.admin, reward, person_id=self.person.id)

    def test_total_earned_ignores_spending(self):
        services.adjust_points(self.admin, person_id=self.person.id, points=100)
        reward = services.create_reward(self.admin, name="Toy", cost_points=30)
        req = services.request_reward(self.admin, reward, person_id=self.person.id)
        services.approve_reward_request(self.admin, req)
        # Balance drops to 70, but lifetime "total earned" stays at 100.
        self.assertEqual(services.get_points_balance(self.person.id), 70)
        self.assertEqual(services.get_total_earned(self.person.id), 100)


# ---------------------------------------------------------------------------
# Routines + streaks
# ---------------------------------------------------------------------------

class RoutineTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", role=User.Role.ADMIN)
        self.child_user = _make_user("kid", role=User.Role.USER, is_child=True)
        self.person = _make_person("Finn", linked_user=self.child_user)

    def test_complete_routine_awards_points_immediately(self):
        routine = services.create_routine(self.admin, title="Brush teeth", points=2)
        services.complete_routine(self.admin, routine, person_id=self.person.id)
        self.assertEqual(services.get_points_balance(self.person.id), 2)

    def test_complete_routine_is_idempotent_per_day(self):
        routine = services.create_routine(self.admin, title="Brush teeth", points=2)
        services.complete_routine(self.admin, routine, person_id=self.person.id)
        services.complete_routine(self.admin, routine, person_id=self.person.id)
        self.assertEqual(services.get_points_balance(self.person.id), 2)
        self.assertTrue(services.completed_today(routine, self.person.id))

    def test_streak_counts_consecutive_days(self):
        from datetime import timedelta
        from apps.core.models import get_active_household
        from apps.meridian.models import MeridianRoutineCompletion
        routine = services.create_routine(self.admin, title="Read", points=1)
        today = timezone.localdate()
        for offset in (2, 1, 0):  # three consecutive days incl. today
            MeridianRoutineCompletion.objects.create(
                household=get_active_household(), routine=routine,
                person_id=self.person.id, completed_date=today - timedelta(days=offset),
            )
        self.assertEqual(services.current_streak(routine, self.person.id), 3)

    def test_streak_breaks_on_gap(self):
        from datetime import timedelta
        from apps.core.models import get_active_household
        from apps.meridian.models import MeridianRoutineCompletion
        routine = services.create_routine(self.admin, title="Read", points=1)
        today = timezone.localdate()
        for offset in (5, 0):  # a gap → streak is just today
            MeridianRoutineCompletion.objects.create(
                household=get_active_household(), routine=routine,
                person_id=self.person.id, completed_date=today - timedelta(days=offset),
            )
        self.assertEqual(services.current_streak(routine, self.person.id), 1)

    def test_void_completion_claws_back_points(self):
        routine = services.create_routine(self.admin, title="Brush teeth", points=2)
        completion = services.complete_routine(self.admin, routine, person_id=self.person.id)
        services.void_routine_completion(self.admin, completion)
        self.assertEqual(services.get_points_balance(self.person.id), 0)
        self.assertFalse(services.completed_today(routine, self.person.id))

    def test_child_can_complete_routine_via_api(self):
        routine = services.create_routine(self.admin, title="Tidy", points=3)
        _login(self.client, "kid")
        resp = self.client.post(reverse("meridian-routine-complete", args=[routine.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["done_today"])
        self.assertEqual(services.get_points_balance(self.person.id), 3)

    def test_child_cannot_create_routine(self):
        _login(self.client, "kid")
        resp = self.client.post(
            reverse("meridian-routine-list"),
            {"title": "x", "points": 1}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# Calendar sync (D7)
# ---------------------------------------------------------------------------

class CalendarSyncTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", role=User.Role.ADMIN)

    def test_dated_task_creates_event(self):
        task = services.create_task(self.admin, title="Walk dog", points=5, due_at=_future())
        task.refresh_from_db()
        self.assertIsNotNone(task.calendar_event_id)
        self.assertTrue(CalendarEvent.objects.filter(pk=task.calendar_event_id).exists())

    def test_undated_task_has_no_event(self):
        task = services.create_task(self.admin, title="Walk dog", points=5)
        self.assertIsNone(task.calendar_event_id)

    def test_updating_due_at_syncs_event(self):
        task = services.create_task(self.admin, title="Walk dog", points=5)
        services.update_task(self.admin, task, due_at=_future())
        task.refresh_from_db()
        self.assertIsNotNone(task.calendar_event_id)

    def test_deleting_task_removes_event(self):
        task = services.create_task(self.admin, title="Walk dog", points=5, due_at=_future())
        task.refresh_from_db()
        event_id = task.calendar_event_id
        services.delete_task(self.admin, task)
        self.assertFalse(CalendarEvent.objects.filter(pk=event_id).exists())


# ---------------------------------------------------------------------------
# Points summary, kiosk, search, visibility
# ---------------------------------------------------------------------------

class PointsAndKioskTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", role=User.Role.ADMIN)
        self.child_user = _make_user("kid", role=User.Role.USER, is_child=True)
        self.child_person = _make_person("Finn", linked_user=self.child_user)

    def test_points_summary_endpoint(self):
        services.adjust_points(self.admin, person_id=self.child_person.id, points=25)
        _login(self.client, "admin")
        resp = self.client.get(reverse("meridian-points"))
        self.assertEqual(resp.status_code, 200)
        summary = resp.json()["summary"]
        self.assertEqual(summary[0]["person_id"], self.child_person.id)
        self.assertEqual(summary[0]["balance"], 25)

    def test_kiosk_endpoint_returns_my_tasks_and_balance(self):
        services.create_task(
            self.admin, title="Tidy", points=5, assigned_to_person_id=self.child_person.id
        )
        services.adjust_points(self.admin, person_id=self.child_person.id, points=12)
        _login(self.client, "kid")
        resp = self.client.get(reverse("kiosk-meridian"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["points_balance"], 12)
        self.assertEqual(len(data["tasks"]), 1)

    def test_search_finds_task(self):
        services.create_task(self.admin, title="Feed the cat", points=5)
        _login(self.client, "admin")
        resp = self.client.get(reverse("meridian-task-list"), {"search": "cat"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_child_cannot_see_private_task(self):
        from apps.meridian.models import Visibility
        services.create_task(self.admin, title="Secret", points=5, visibility=Visibility.PRIVATE)
        _login(self.client, "kid")
        resp = self.client.get(reverse("meridian-task-list"))
        self.assertEqual(len(resp.json()), 0)


# ---------------------------------------------------------------------------
# Data import (D14)
# ---------------------------------------------------------------------------

class ImportCommandTests(TestCase):
    _EXPORT = {
        "users": [{"meridian_id": 1, "display_name": "Finn"}],
        "categories": [{"meridian_id": 7, "name": "Bedroom", "colour": "#50C878"}],
        "tasks": [{"title": "Tidy room", "points": 10,
                   "category_meridian_id": 7, "assigned_user_meridian_id": 1}],
        "rewards": [{"name": "Movie night", "cost_points": 30}],
        "points_entries": [{"user_meridian_id": 1, "points": 45, "reason": "Imported balance"}],
        "reward_requests": [{"reward_name": "Movie night", "user_meridian_id": 1,
                             "status": "approved", "points_spent": 30}],
    }

    def _write_export(self) -> str:
        import json
        import tempfile
        fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(self._EXPORT, fh)
        fh.close()
        return fh.name

    def test_dry_run_writes_nothing(self):
        from django.core.management import call_command
        call_command("import_meridian", file=self._write_export(), dry_run=True)
        self.assertEqual(MeridianTask.objects.count(), 0)
        self.assertEqual(MeridianReward.objects.count(), 0)

    def test_import_creates_records(self):
        from django.core.management import call_command
        call_command("import_meridian", file=self._write_export())
        self.assertEqual(Person.objects.filter(display_name="Finn").count(), 1)
        self.assertEqual(MeridianTask.objects.count(), 1)
        self.assertEqual(MeridianReward.objects.count(), 1)
        person = Person.objects.get(display_name="Finn")
        self.assertEqual(services.get_points_balance(person.id), 45)

    def test_import_is_idempotent(self):
        from django.core.management import call_command
        path = self._write_export()
        call_command("import_meridian", file=path)
        call_command("import_meridian", file=path)
        self.assertEqual(MeridianTask.objects.count(), 1)
        self.assertEqual(MeridianReward.objects.count(), 1)
