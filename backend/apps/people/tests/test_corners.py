from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import Household
from apps.nodes.models import HouseholdNode
from apps.fitness.models import WorkoutSession
from apps.people.models import CornerReaction, Person


class CornerApiTests(TestCase):
    def setUp(self):
        self.household = Household.objects.first() or Household.objects.create(name="Corner home", slug="corner-home", timezone="Australia/Brisbane")
        HouseholdNode.objects.filter(household=self.household, node__key="fitness").update(is_enabled=True)
        self.alex_user = User.objects.create_user("corner_alex", "Alex", password="pw", role=User.Role.USER)
        self.sam_user = User.objects.create_user("corner_sam", "Sam", password="pw", role=User.Role.USER)
        self.alex = Person.objects.create(
            household=self.household, linked_user=self.alex_user, display_name="Alex",
            created_by=self.alex_user, updated_by=self.alex_user,
        )
        self.sam = Person.objects.create(
            household=self.household, linked_user=self.sam_user, display_name="Sam",
            created_by=self.alex_user, updated_by=self.alex_user,
        )
        self.public_session = WorkoutSession.objects.create(
            household=self.household, person=self.alex, name="Upper body", status="completed",
            started_at=timezone.now(), finished_at=timezone.now(), duration_seconds=1800,
            total_reps=40, visibility="household", created_by=self.alex_user, updated_by=self.alex_user,
        )
        WorkoutSession.objects.create(
            household=self.household, person=self.alex, name="Private training", status="completed",
            started_at=timezone.now(), finished_at=timezone.now(), visibility="private",
            created_by=self.alex_user, updated_by=self.alex_user,
        )

    def test_corner_hides_another_users_private_activity(self):
        self.client.force_login(self.sam_user)
        response = self.client.get(reverse("corner-detail", args=[self.alex.id]))
        self.assertEqual(response.status_code, 200)
        titles = [row["title"] for row in response.json()["activity"]]
        self.assertIn("Completed Upper body", titles)
        self.assertNotIn("Completed Private training", titles)

    def test_fitness_activity_links_to_the_session_and_has_expandable_detail(self):
        self.client.force_login(self.sam_user)
        response = self.client.get(reverse("corner-detail", args=[self.alex.id]))
        row = next(
            item for item in response.json()["activity"]
            if item["key"] == f"fitness:session:{self.public_session.id}:completed"
        )
        self.assertEqual(row["action_url"], f"/fitness?tab=history&session={self.public_session.id}")
        self.assertEqual(row["detail_summary"]["duration_seconds"], 1800)
        self.assertEqual(row["detail_summary"]["total_reps"], 40)
        self.assertEqual(row["detail_summary"]["exercises"], [])

    def test_reaction_toggles_and_is_returned_on_visible_activity(self):
        self.client.force_login(self.sam_user)
        key = f"fitness:session:{self.public_session.id}:completed"
        url = reverse("corner-reaction", args=[self.alex.id])
        response = self.client.post(url, {"activity_key": key, "emoji": "❤️"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["active"])
        self.assertEqual(CornerReaction.objects.count(), 1)
        reaction = next(row for row in response.json()["corner"]["activity"] if row["key"] == key)["reactions"][0]
        self.assertEqual(reaction["count"], 1)
        self.assertTrue(reaction["mine"])
        response = self.client.post(url, {"activity_key": key, "emoji": "❤️"}, content_type="application/json")
        self.assertFalse(response.json()["active"])
        self.assertEqual(CornerReaction.objects.count(), 0)
        response = self.client.post(url, {"activity_key": key, "emoji": "❤️"}, content_type="application/json")
        self.assertTrue(response.json()["active"])
        self.assertEqual(CornerReaction.objects.count(), 1)

    def test_cannot_react_to_private_activity_the_viewer_cannot_see(self):
        private = WorkoutSession.objects.get(name="Private training")
        self.client.force_login(self.sam_user)
        response = self.client.post(
            reverse("corner-reaction", args=[self.alex.id]),
            {"activity_key": f"fitness:session:{private.id}:completed", "emoji": "👍"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(CornerReaction.objects.count(), 0)
