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
    MeridianCategory,
    MeridianPointsEntry,
    MeridianReward,
    MeridianRewardRequest,
    MeridianTask,
    MeridianTaskCompletion,
    MeridianWishlistRequest,
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
        self.assertEqual(
            MeridianTaskCompletion.objects.get(task=task).status,
            MeridianTaskCompletion.Status.APPROVED,
        )

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

    def test_per_person_task_allows_separate_pending_completions(self):
        other = _make_person("Avery")
        task = services.create_task(
            self.admin,
            title="Read",
            points=4,
            completion_scope=MeridianTask.CompletionScope.PER_PERSON,
        )
        first = services.submit_task_completion(self.admin, task, person_id=self.person.id)
        second = services.submit_task_completion(self.admin, task, person_id=other.id)
        self.assertNotEqual(first.id, second.id)
        self.assertEqual(MeridianTaskCompletion.objects.filter(task=task).count(), 2)

    def test_household_task_blocks_after_one_active_completion(self):
        other = _make_person("Avery")
        task = services.create_task(
            self.admin,
            title="Take bins out",
            points=4,
            completion_scope=MeridianTask.CompletionScope.HOUSEHOLD,
        )
        first = services.submit_task_completion(self.admin, task, person_id=self.person.id)
        second = services.submit_task_completion(self.admin, task, person_id=other.id)
        self.assertEqual(first.id, second.id)
        self.assertEqual(MeridianTaskCompletion.objects.filter(task=task).count(), 1)

    def test_completion_endpoint_approves_specific_submission(self):
        task = services.create_task(self.admin, title="Sweep", points=6)
        completion = services.submit_task_completion(self.admin, task, person_id=self.person.id)
        _login(self.client, "admin")
        resp = self.client.post(
            reverse("meridian-task-completion-approve", args=[completion.id]),
            {"review_note": "Looks good"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        completion.refresh_from_db()
        self.assertEqual(completion.status, MeridianTaskCompletion.Status.APPROVED)
        self.assertEqual(completion.review_note, "Looks good")
        self.assertEqual(services.get_points_balance(self.person.id), 6)


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

    def test_stock_runs_out(self):
        services.adjust_points(self.admin, person_id=self.person.id, points=100)
        other = _make_person("Mara")
        services.adjust_points(self.admin, person_id=other.id, points=100)
        reward = services.create_reward(self.admin, name="Last toy", cost_points=10, quantity=1)
        services.request_reward(self.admin, reward, person_id=self.person.id)
        self.assertEqual(reward.remaining_stock(), 0)
        with self.assertRaises(services.MeridianError):
            services.request_reward(self.admin, reward, person_id=other.id)

    def test_daily_limit_enforced(self):
        services.adjust_points(self.admin, person_id=self.person.id, points=100)
        reward = services.create_reward(
            self.admin, name="Screen time", cost_points=5, daily_limit_per_user=1
        )
        services.request_reward(self.admin, reward, person_id=self.person.id)
        with self.assertRaises(services.MeridianError):
            services.request_reward(self.admin, reward, person_id=self.person.id)

    def test_cart_checkout_is_all_or_nothing(self):
        services.adjust_points(self.admin, person_id=self.person.id, points=25)
        cheap = services.create_reward(self.admin, name="Sticker", cost_points=10)
        pricey = services.create_reward(self.admin, name="Big toy", cost_points=20)
        # 25 points can't cover 10 + 20 → whole checkout rolls back, nothing reserved.
        with self.assertRaises(services.MeridianError):
            services.checkout_cart(
                self.admin, person_id=self.person.id, reward_ids=[cheap.id, pricey.id]
            )
        self.assertEqual(services.get_points_balance(self.person.id), 25)
        self.assertEqual(MeridianRewardRequest.objects.count(), 0)

    def test_cart_checkout_succeeds(self):
        services.adjust_points(self.admin, person_id=self.person.id, points=40)
        a = services.create_reward(self.admin, name="Sticker", cost_points=10)
        b = services.create_reward(self.admin, name="Comic", cost_points=20)
        reqs = services.checkout_cart(
            self.admin, person_id=self.person.id, reward_ids=[a.id, b.id]
        )
        self.assertEqual(len(reqs), 2)
        self.assertEqual(services.get_points_balance(self.person.id), 10)

    def test_total_earned_ignores_spending(self):
        services.adjust_points(self.admin, person_id=self.person.id, points=100)
        reward = services.create_reward(self.admin, name="Toy", cost_points=30)
        req = services.request_reward(self.admin, reward, person_id=self.person.id)
        services.approve_reward_request(self.admin, req)
        # Balance drops to 70, but lifetime "total earned" stays at 100.
        self.assertEqual(services.get_points_balance(self.person.id), 70)
        self.assertEqual(services.get_total_earned(self.person.id), 100)

    def test_reward_category_is_serialized(self):
        category = services.create_category(
            self.admin, name="Treats", kind=MeridianCategory.Kind.REWARD
        )
        reward = services.create_reward(
            self.admin, name="Ice cream", cost_points=30, category_id=category.id
        )
        _login(self.client, "admin")
        resp = self.client.get(reverse("meridian-reward-detail", args=[reward.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["category_id"], category.id)


# ---------------------------------------------------------------------------
# Routines + streaks
# ---------------------------------------------------------------------------

class RewardPriceVisibilityTests(TestCase):
    """Estimated cost (`price_estimate`) is admin-only in the shop (owner request)."""

    def setUp(self):
        self.admin = _make_user("admin", role=User.Role.ADMIN)
        self.user = _make_user("parentuser", role=User.Role.USER)
        services.create_reward(
            self.admin, name="Bike", cost_points=500, price_estimate="120.00"
        )
        self.list_url = reverse("meridian-reward-list")

    def test_admin_sees_price_estimate(self):
        _login(self.client, "admin")
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("price_estimate", resp.json()[0])

    def test_non_admin_does_not_see_price_estimate(self):
        _login(self.client, "parentuser")
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("price_estimate", resp.json()[0])


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
        # With auto-end on, a gap resets the streak to just today.
        self.assertEqual(services.current_streak(routine, self.person.id, auto_end=True), 1)

    def test_auto_end_setting_controls_streak_breaking(self):
        from datetime import timedelta
        from apps.core.models import get_active_household
        from apps.meridian import config
        from apps.meridian.models import MeridianRoutineCompletion
        routine = services.create_routine(self.admin, title="Read", points=1)
        today = timezone.localdate()
        for offset in (5, 0):  # a gap of several days
            MeridianRoutineCompletion.objects.create(
                household=get_active_household(), routine=routine,
                person_id=self.person.id, completed_date=today - timedelta(days=offset),
            )
        # Default (auto_end_streaks=False): streak is total completion days, gaps ignored.
        self.assertEqual(services.current_streak(routine, self.person.id), 2)
        # Turn auto-end on via the household setting → gap breaks the streak.
        config.update_settings(self.admin, {"auto_end_streaks": True})
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
# Group goals
# ---------------------------------------------------------------------------

class GroupGoalTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", role=User.Role.ADMIN)
        self.child_user = _make_user("kid", role=User.Role.USER, is_child=True)
        self.person = _make_person("Finn", linked_user=self.child_user)

    def test_contribute_reserves_points_and_tracks_progress(self):
        services.adjust_points(self.admin, person_id=self.person.id, points=50)
        goal = services.create_goal(self.admin, title="Family trip", target_points=100)
        services.contribute_to_goal(self.admin, goal, person_id=self.person.id, amount=30)
        self.assertEqual(services.get_points_balance(self.person.id), 20)
        self.assertEqual(goal.total_contributed(), 30)
        self.assertEqual(goal.progress_percentage(), 30)

    def test_goal_marked_funded_when_target_reached(self):
        services.adjust_points(self.admin, person_id=self.person.id, points=100)
        goal = services.create_goal(self.admin, title="Trampoline", target_points=40)
        services.contribute_to_goal(self.admin, goal, person_id=self.person.id, amount=40)
        goal.refresh_from_db()
        self.assertEqual(goal.status, "funded")
        self.assertTrue(goal.is_funded())

    def test_cannot_contribute_more_than_balance(self):
        services.adjust_points(self.admin, person_id=self.person.id, points=10)
        goal = services.create_goal(self.admin, title="Trip", target_points=100)
        with self.assertRaises(services.MeridianError):
            services.contribute_to_goal(self.admin, goal, person_id=self.person.id, amount=20)

    def test_refund_contribution_returns_points(self):
        services.adjust_points(self.admin, person_id=self.person.id, points=50)
        goal = services.create_goal(self.admin, title="Trip", target_points=100)
        contribution = services.contribute_to_goal(self.admin, goal, person_id=self.person.id, amount=30)
        services.refund_goal_contribution(self.admin, contribution)
        self.assertEqual(services.get_points_balance(self.person.id), 50)
        self.assertEqual(goal.total_contributed(), 0)

    def test_child_can_contribute_via_api(self):
        services.adjust_points(self.admin, person_id=self.person.id, points=50)
        goal = services.create_goal(self.admin, title="Trip", target_points=100)
        _login(self.client, "kid")
        resp = self.client.post(
            reverse("meridian-goal-contribute", args=[goal.id]),
            {"amount": 25}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(services.get_points_balance(self.person.id), 25)

    def test_child_cannot_create_goal(self):
        _login(self.client, "kid")
        resp = self.client.post(
            reverse("meridian-goal-list"),
            {"title": "x", "target_points": 10}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# Wishlist
# ---------------------------------------------------------------------------

class WishlistTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", role=User.Role.ADMIN)
        self.child_user = _make_user("kid", role=User.Role.USER, is_child=True)
        self.person = _make_person("Finn", linked_user=self.child_user)

    def test_request_then_approve_creates_item(self):
        req = services.request_wishlist_item(
            self.admin, person_id=self.person.id, requested_name="Lego set"
        )
        item = services.approve_wishlist_request(self.admin, req, point_cost=80)
        req.refresh_from_db()
        self.assertEqual(req.status, "approved")
        self.assertEqual(item.name, "Lego set")
        self.assertEqual(item.point_cost, 80)

    def test_contribute_saves_toward_item_and_funds_it(self):
        services.adjust_points(self.admin, person_id=self.person.id, points=100)
        item = services.create_wishlist_item(
            self.admin, person_id=self.person.id, name="Lego set", point_cost=60
        )
        services.contribute_to_wishlist(self.admin, item, person_id=self.person.id, amount=60)
        self.assertEqual(services.get_points_balance(self.person.id), 40)
        item.refresh_from_db()
        self.assertEqual(item.status, "funded")

    def test_refund_wishlist_contribution(self):
        services.adjust_points(self.admin, person_id=self.person.id, points=50)
        item = services.create_wishlist_item(
            self.admin, person_id=self.person.id, name="Book", point_cost=100
        )
        contribution = services.contribute_to_wishlist(
            self.admin, item, person_id=self.person.id, amount=30
        )
        services.refund_wishlist_contribution(self.admin, contribution)
        self.assertEqual(services.get_points_balance(self.person.id), 50)

    def test_child_can_request_item_via_api(self):
        _login(self.client, "kid")
        resp = self.client.post(
            reverse("meridian-wishlist-request-list"),
            {"requested_name": "Skateboard"}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(MeridianWishlistRequest.objects.count(), 1)

    def test_child_cannot_approve_wishlist_request(self):
        req = services.request_wishlist_item(
            self.admin, person_id=self.person.id, requested_name="Skateboard"
        )
        _login(self.client, "kid")
        resp = self.client.post(
            reverse("meridian-wishlist-request-approve", args=[req.id]),
            {"point_cost": 50}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# Settings + reports + category kinds — Phase 2.17
# ---------------------------------------------------------------------------

class SettingsAndReportsTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", role=User.Role.ADMIN)
        self.child_user = _make_user("kid", role=User.Role.USER, is_child=True)
        self.person = _make_person("Finn", linked_user=self.child_user)

    def test_settings_defaults_and_update(self):
        from apps.meridian import config
        self.assertEqual(config.get_settings()["points_label"], "points")
        config.update_settings(self.admin, {"points_label": "stars", "group_goals_enabled": False})
        s = config.get_settings()
        self.assertEqual(s["points_label"], "stars")
        self.assertFalse(s["group_goals_enabled"])

    def test_disabled_group_goals_blocks_contribution(self):
        from apps.meridian import config
        services.adjust_points(self.admin, person_id=self.person.id, points=50)
        goal = services.create_goal(self.admin, title="Trip", target_points=100)
        config.update_settings(self.admin, {"group_goals_enabled": False})
        with self.assertRaises(services.MeridianError):
            services.contribute_to_goal(self.admin, goal, person_id=self.person.id, amount=10)

    def test_disabled_wishlist_blocks_requests(self):
        from apps.meridian import config
        config.update_settings(self.admin, {"wishlist_requests_enabled": False})
        with self.assertRaises(services.MeridianError):
            services.request_wishlist_item(self.admin, person_id=self.person.id, requested_name="Toy")

    def test_settings_endpoint_patch_requires_manager(self):
        _login(self.client, "kid")
        resp = self.client.patch(
            reverse("meridian-settings"), {"points_label": "x"}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_reports_leaderboard(self):
        services.adjust_points(self.admin, person_id=self.person.id, points=40)
        _login(self.client, "admin")
        resp = self.client.get(reverse("meridian-reports"))
        self.assertEqual(resp.status_code, 200)
        board = resp.json()["leaderboard"]
        self.assertEqual(board[0]["person_id"], self.person.id)
        self.assertEqual(board[0]["total_earned"], 40)

    def test_category_kind_filter(self):
        from apps.meridian.models import MeridianCategory
        services.create_category(self.admin, name="Bedroom", kind=MeridianCategory.Kind.TASK)
        services.create_category(self.admin, name="Treats", kind=MeridianCategory.Kind.REWARD)
        _login(self.client, "admin")
        resp = self.client.get(reverse("meridian-category-list"), {"kind": "reward"})
        self.assertEqual(resp.status_code, 200)
        names = [c["name"] for c in resp.json()]
        self.assertEqual(names, ["Treats"])


# ---------------------------------------------------------------------------
# Scheduled work (allowance, perfect-month) — Phase 2.16
# ---------------------------------------------------------------------------

class ScheduledWorkTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", role=User.Role.ADMIN)
        self.person = _make_person("Finn")

    def test_allowance_awarded_on_matching_weekday(self):
        from datetime import date
        from apps.core.models import get_active_household
        from apps.meridian.models import MeridianAllowance
        # A Monday.
        monday = date(2026, 6, 22)
        self.assertEqual(monday.weekday(), 0)
        MeridianAllowance.objects.create(
            household=get_active_household(), person=self.person, amount=15, weekday=0,
        )
        awarded = services.award_allowances(on=monday)
        self.assertEqual(awarded, 1)
        self.assertEqual(services.get_points_balance(self.person.id), 15)

    def test_allowance_skipped_on_other_weekday(self):
        from datetime import date
        from apps.core.models import get_active_household
        from apps.meridian.models import MeridianAllowance
        MeridianAllowance.objects.create(
            household=get_active_household(), person=self.person, amount=15, weekday=0,
        )
        tuesday = date(2026, 6, 23)
        self.assertEqual(services.award_allowances(on=tuesday), 0)
        self.assertEqual(services.get_points_balance(self.person.id), 0)

    def test_allowance_is_idempotent_per_day(self):
        from datetime import date
        from apps.core.models import get_active_household
        from apps.meridian.models import MeridianAllowance
        monday = date(2026, 6, 22)
        MeridianAllowance.objects.create(
            household=get_active_household(), person=self.person, amount=15, weekday=0,
        )
        services.award_allowances(on=monday)
        services.award_allowances(on=monday)  # second run same day → no double-pay
        self.assertEqual(services.get_points_balance(self.person.id), 15)

    def test_allowance_config_endpoint_upserts(self):
        _login(self.client, "admin")
        resp = self.client.patch(
            reverse("meridian-allowances"),
            {"results": [{"person_id": self.person.id, "amount": 20, "weekday": 4, "is_active": True}]},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        from apps.meridian.models import MeridianAllowance
        allowance = MeridianAllowance.objects.get(person=self.person)
        self.assertEqual(allowance.amount, 20)
        self.assertEqual(allowance.weekday, 4)
        self.assertTrue(allowance.is_active)

    def test_non_manager_cannot_patch_allowance_config(self):
        user = _make_user("parentuser", role=User.Role.USER)
        _make_person("Parent", linked_user=user)
        _login(self.client, "parentuser")
        resp = self.client.patch(
            reverse("meridian-allowances"),
            {"results": [{"person_id": self.person.id, "amount": 20, "weekday": 4, "is_active": True}]},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_perfect_month_awards_badge(self):
        import calendar
        from datetime import date
        from apps.core.models import get_active_household
        from apps.achievements.models import PersonBadge
        from apps.meridian.models import MeridianRoutine, MeridianRoutineCompletion
        routine = services.create_routine(self.admin, title="Brush teeth", points=1)
        year, month = 2025, 2
        for day in range(1, calendar.monthrange(year, month)[1] + 1):
            MeridianRoutineCompletion.objects.create(
                household=get_active_household(), routine=routine, person_id=self.person.id,
                completed_date=date(year, month, day),
            )
        emitted = services.award_perfect_month_badges(year=year, month=month)
        self.assertEqual(emitted, 1)
        self.assertTrue(
            PersonBadge.objects.filter(person=self.person, badge__code="routine_perfect_month").exists()
        )

    def test_command_runs(self):
        from django.core.management import call_command
        call_command("meridian_run_scheduled", date="2026-06-22")


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


class FullImportCommandTests(TestCase):
    """The extended importer (Phase 2.18): routines, goals, wishlist, badges, allowances."""

    _EXPORT = {
        "users": [{"meridian_id": 1, "display_name": "Finn"}],
        "points_entries": [
            {"user_meridian_id": 1, "points": 100, "reason": "earned",
             "transaction_type": "task_approved"},
        ],
        "tasks": [{"title": "Tidy room", "points": 10, "assigned_user_meridian_id": 1}],
        "task_completions": [
            {"task_title": "Tidy room", "user_meridian_id": 1, "status": "approved",
             "submitted_at": "2026-06-01T08:00:00Z", "reviewed_at": "2026-06-01T18:00:00Z",
             "review_note": "Great work"},
        ],
        "routines": [{"title": "Brush teeth", "points": 2, "assigned_user_meridian_id": 1}],
        "routine_completions": [
            {"routine_title": "Brush teeth", "user_meridian_id": 1, "completed_date": "2026-06-01"},
        ],
        "group_goals": [{"title": "Family trip", "target_points": 500}],
        "group_goal_contributions": [
            {"goal_title": "Family trip", "user_meridian_id": 1, "amount": 20},
        ],
        "wishlist_items": [{"user_meridian_id": 1, "name": "Lego", "point_cost": 80}],
        "wishlist_contributions": [
            {"item_name": "Lego", "user_meridian_id": 1, "amount": 15},
        ],
        "badges": [{"user_meridian_id": 1, "badge_code": "first_task"}],
        "allowances": [{"user_meridian_id": 1, "amount": 10, "weekday": 0}],
    }

    def _write_export(self) -> str:
        import json
        import tempfile
        fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(self._EXPORT, fh)
        fh.close()
        return fh.name

    def test_full_import_creates_all_entities(self):
        from django.core.management import call_command
        from apps.achievements.models import PersonBadge
        from apps.meridian.models import (
            MeridianAllowance, MeridianGroupGoal, MeridianRoutine,
            MeridianTaskCompletion, MeridianWishlistItem,
        )
        call_command("import_meridian", file=self._write_export())
        person = Person.objects.get(display_name="Finn")
        self.assertEqual(services.get_points_balance(person.id), 100)
        completion = MeridianTaskCompletion.objects.get(person=person, task__title="Tidy room")
        self.assertEqual(completion.status, "approved")
        self.assertEqual(completion.review_note, "Great work")
        self.assertIsNotNone(completion.reviewed_at)
        self.assertEqual(services.get_total_earned(person.id), 100)  # task_approved counts
        self.assertEqual(MeridianRoutine.objects.count(), 1)
        self.assertTrue(services.completed_today(
            MeridianRoutine.objects.first(), person.id, on=__import__("datetime").date(2026, 6, 1)
        ))
        self.assertEqual(MeridianGroupGoal.objects.first().total_contributed(), 20)
        self.assertEqual(MeridianWishlistItem.objects.first().total_saved(), 15)
        self.assertTrue(PersonBadge.objects.filter(person=person, badge__code="first_task").exists())
        self.assertEqual(MeridianAllowance.objects.get(person=person).amount, 10)

    def test_full_import_idempotent_entities(self):
        from django.core.management import call_command
        from apps.meridian.models import (
            MeridianGroupGoal, MeridianRoutine, MeridianTaskCompletion, MeridianWishlistItem,
        )
        path = self._write_export()
        call_command("import_meridian", file=path)
        call_command("import_meridian", file=path)
        self.assertEqual(MeridianRoutine.objects.count(), 1)
        self.assertEqual(MeridianGroupGoal.objects.count(), 1)
        self.assertEqual(MeridianWishlistItem.objects.count(), 1)
        self.assertEqual(MeridianTaskCompletion.objects.count(), 1)
