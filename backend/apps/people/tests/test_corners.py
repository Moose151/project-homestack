from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import Household
from apps.nodes.models import HouseholdNode
from apps.fitness.models import WorkoutSession
from apps.atlas.services import create_atlas_list, create_list_item
from apps.people.models import CornerReaction, Person
from apps.scheduling.services import create_event


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


class CornerCalendarProjectionTests(TestCase):
    """The Calendar had no Corner provider, so adding a shared appointment showed up in nobody's
    recent activity and an appointment assigned to someone never reached their assignments."""

    def setUp(self):
        self.household = Household.objects.first() or Household.objects.create(
            name="Corner home", slug="corner-home", timezone="Australia/Brisbane",
        )
        self.alex_user = User.objects.create_user("cal_alex", "Alex", password="pw", role=User.Role.USER)
        self.sam_user = User.objects.create_user("cal_sam", "Sam", password="pw", role=User.Role.USER)
        self.alex = Person.objects.create(
            household=self.household, linked_user=self.alex_user, display_name="Alex",
            created_by=self.alex_user, updated_by=self.alex_user,
        )
        self.sam = Person.objects.create(
            household=self.household, linked_user=self.sam_user, display_name="Sam",
            created_by=self.alex_user, updated_by=self.alex_user,
        )

    def _corner(self, viewer, person):
        self.client.force_login(viewer)
        return self.client.get(reverse("corner-detail", args=[person.id])).json()

    def test_adding_an_event_appears_in_the_creators_recent_activity(self):
        create_event(self.alex_user, title="Dentist", start_at=timezone.now() + timezone.timedelta(days=2))
        titles = [row["title"] for row in self._corner(self.sam_user, self.alex)["activity"]]
        self.assertIn("Added Dentist", titles)

    def test_an_event_assigned_to_someone_appears_under_their_assignments(self):
        event = create_event(
            self.alex_user, title="Physio", start_at=timezone.now() + timezone.timedelta(days=2),
            assigned_to_people=[self.sam],
        )
        assignments = self._corner(self.alex_user, self.sam)["assignments"]
        self.assertIn("Physio", [row["title"] for row in assignments])
        row = next(item for item in assignments if item["title"] == "Physio")
        self.assertEqual(row["source_node"], "scheduling")
        self.assertIn(f"event={event.id}", row["action_url"])

    def test_a_private_event_stays_out_of_another_persons_view(self):
        create_event(
            self.alex_user, title="Secret", start_at=timezone.now() + timezone.timedelta(days=2),
            visibility="private",
        )
        titles = [row["title"] for row in self._corner(self.sam_user, self.alex)["activity"]]
        self.assertNotIn("Added Secret", titles)

    def test_an_event_hidden_from_the_viewer_stays_out_of_their_view(self):
        create_event(
            self.alex_user, title="Surprise party", start_at=timezone.now() + timezone.timedelta(days=2),
            hidden_from_users=[self.sam_user],
        )
        titles = [row["title"] for row in self._corner(self.sam_user, self.alex)["activity"]]
        self.assertNotIn("Added Surprise party", titles)

    def test_a_node_backed_event_is_left_to_its_owning_node(self):
        # An Atlas to-do mirrors into the calendar; Atlas already projects it, so the mirrored
        # CalendarEvent must not list the same thing a second time.
        atlas_list = create_atlas_list(self.alex_user, title="Jobs", list_type="todo")
        create_list_item(
            self.alex_user, atlas_list, title="Book the car in",
            due_at=timezone.now() + timezone.timedelta(days=2),
        )
        activity = self._corner(self.sam_user, self.alex)["activity"]
        self.assertEqual(
            [row["title"] for row in activity if row["source_node"] == "scheduling"], [],
        )
