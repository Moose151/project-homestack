"""Achievements tests (Milestone 2, Phase 2.14, D20).

Covers the cross-node, event-driven design: Meridian domain events award badges via the bus
without Meridian ever calling the achievements app directly. Awarding is idempotent.
"""
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.achievements import services
from apps.achievements.models import Badge, PersonBadge
from apps.meridian import services as meridian
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


class BadgeAwardingTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin")
        self.person = _make_person("Finn")

    def test_badges_are_seeded(self):
        self.assertEqual(Badge.objects.filter(code="first_task").count(), 1)
        self.assertEqual(Badge.objects.count(), 15)

    def test_first_approved_task_awards_first_task_badge(self):
        task = meridian.create_task(
            self.admin, title="Tidy", points=5, assigned_to_person_id=self.person.id
        )
        meridian.complete_task(self.admin, task, person_id=self.person.id)
        meridian.approve_task(self.admin, task)
        self.assertTrue(
            PersonBadge.objects.filter(person=self.person, badge__code="first_task").exists()
        )

    def test_task_milestones_via_event_bus(self):
        for i in range(5):
            t = meridian.create_task(self.admin, title=f"T{i}", points=1,
                                     assigned_to_person_id=self.person.id)
            meridian.complete_task(self.admin, t, person_id=self.person.id)
            meridian.approve_task(self.admin, t)
        codes = set(PersonBadge.objects.filter(person=self.person).values_list("badge__code", flat=True))
        self.assertIn("first_task", codes)
        self.assertIn("five_tasks", codes)
        self.assertNotIn("ten_tasks", codes)

    def test_total_earned_badge(self):
        # 100+ earned points (manual adjustment is an earning type) → Big Earner.
        meridian.adjust_points(self.admin, person_id=self.person.id, points=120)
        self.assertTrue(
            PersonBadge.objects.filter(person=self.person, badge__code="hundred_points_earned").exists()
        )

    def test_group_contribution_badge(self):
        meridian.adjust_points(self.admin, person_id=self.person.id, points=50)
        goal = meridian.create_goal(self.admin, title="Trip", target_points=100)
        meridian.contribute_to_goal(self.admin, goal, person_id=self.person.id, amount=10)
        self.assertTrue(
            PersonBadge.objects.filter(person=self.person, badge__code="group_contributor").exists()
        )

    def test_awarding_is_idempotent(self):
        services.award_badge(self.person.id, "first_task")
        services.award_badge(self.person.id, "first_task")
        self.assertEqual(
            PersonBadge.objects.filter(person=self.person, badge__code="first_task").count(), 1
        )

    def test_unknown_badge_code_is_ignored(self):
        pb, created = services.award_badge(self.person.id, "does_not_exist")
        self.assertIsNone(pb)
        self.assertFalse(created)


class BadgeApiTests(TestCase):
    def setUp(self):
        self.child_user = _make_user("kid", role=User.Role.USER, is_child=True)
        self.person = _make_person("Finn", linked_user=self.child_user)

    def _login(self):
        self.client.post(
            reverse("auth-pin-login"),
            {"username": "kid", "pin": "1234"}, content_type="application/json",
        )

    def test_badge_catalogue_endpoint(self):
        self._login()
        resp = self.client.get(reverse("achievements-badge-list"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 15)

    def test_my_badges_endpoint(self):
        services.award_badge(self.person.id, "first_task")
        self._login()
        resp = self.client.get(reverse("achievements-person-badges"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["badge"]["code"], "first_task")
