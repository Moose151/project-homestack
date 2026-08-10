from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.fitness.models import Exercise, PersonalRecord, WorkoutSession
from apps.people.models import Person


class FitnessAPITestsMixin:
    def make_user(self, username, role="admin", child=False):
        return User.objects.create_user(
            username=username, display_name=username.title(), role=role,
            is_child_account=child, password="test-pass-123",
        )


from django.test import TestCase


class FitnessPermissionTests(FitnessAPITestsMixin, TestCase):
    """Permission spine is the first acceptance gate for the social Fitness node (D10)."""

    def setUp(self):
        self.admin = self.make_user("fitness-admin")
        self.child = self.make_user("fitness-child", role="user", child=True)
        self.client = APIClient()

    def test_anonymous_cannot_list_exercises(self):
        self.assertEqual(self.client.get("/api/v1/fitness/exercises/").status_code, 403)

    def test_child_can_view_but_cannot_create_exercise(self):
        self.client.force_authenticate(self.child)
        self.assertEqual(self.client.get("/api/v1/fitness/exercises/").status_code, 200)
        self.assertEqual(self.client.post("/api/v1/fitness/exercises/", {
            "name": "Unsafe write", "exercise_type": "strength", "measurement": "reps_only",
        }, format="json").status_code, 403)


class FitnessWorkflowTests(FitnessAPITestsMixin, TestCase):
    def setUp(self):
        self.user = self.make_user("coach")
        self.person = Person.objects.create(
            household=get_active_household(), linked_user=self.user,
            display_name="Coach", created_by=self.user, updated_by=self.user,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.exercise = Exercise.objects.create(
            household=get_active_household(), name="Barbell squat", exercise_type="strength",
            muscle_group="Legs", measurement="reps_weight", created_by=self.user, updated_by=self.user,
        )

    def test_program_to_completed_session_and_records(self):
        response = self.client.post("/api/v1/fitness/programs/", {
            "name": "Three day strength", "person_ids": [self.person.id],
            "workouts": [{"name": "Day one", "position": 0, "exercises": [{
                "exercise_id": self.exercise.id, "target_sets": 1, "target_reps": 5,
            }]}],
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        workout_id = response.data["workouts"][0]["id"]
        response = self.client.post("/api/v1/fitness/sessions/start/", {
            "person_id": self.person.id, "workout_id": workout_id,
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        session_id = response.data["id"]
        set_id = response.data["exercises"][0]["sets"][0]["id"]
        response = self.client.patch(f"/api/v1/fitness/session-sets/{set_id}/", {
            "reps": 5, "weight": "100.00", "is_completed": True,
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.post(f"/api/v1/fitness/sessions/{session_id}/finish/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        session = WorkoutSession.objects.get(pk=session_id)
        self.assertEqual(session.total_reps, 5)
        self.assertEqual(session.total_volume, 500)
        self.assertEqual(PersonalRecord.objects.filter(session=session).count(), 3)

    def _completed_session(self, sets, *, visibility="household", person=None):
        """Log and finish one session of the shared exercise, returning its id."""
        person = person or self.person
        response = self.client.post("/api/v1/fitness/sessions/start/", {
            "person_id": person.id, "name": "Previous workout", "visibility": visibility,
        }, format="json")
        session_id = response.data["id"]
        response = self.client.post(f"/api/v1/fitness/sessions/{session_id}/exercises/", {
            "exercise_id": self.exercise.id, "target_sets": len(sets),
        }, format="json")
        for set_data, row in zip(sets, response.data["sets"]):
            self.client.patch(f"/api/v1/fitness/session-sets/{row['id']}/", {
                **set_data, "is_completed": True,
            }, format="json")
        self.client.post(f"/api/v1/fitness/sessions/{session_id}/finish/", {}, format="json")
        return session_id

    def _start_program_session(self, *, target_sets=1, target_weight=None):
        response = self.client.post("/api/v1/fitness/programs/", {
            "name": "Strength", "person_ids": [self.person.id],
            "workouts": [{"name": "Day one", "position": 0, "exercises": [{
                "exercise_id": self.exercise.id, "target_sets": target_sets, "target_reps": 5,
                "target_weight": target_weight,
            }]}],
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        response = self.client.post("/api/v1/fitness/sessions/start/", {
            "person_id": self.person.id, "workout_id": response.data["workouts"][0]["id"],
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_program_session_prefills_the_weight_last_lifted(self):
        self._completed_session([{"reps": 5, "weight": "102.50"}])
        data = self._start_program_session(target_weight="60.00")
        entry = data["exercises"][0]
        self.assertEqual(entry["sets"][0]["weight"], "102.50")
        self.assertEqual(entry["last_performance"]["sets"][0]["weight"], "102.50")

    def test_prefill_matches_each_set_position_then_repeats_the_final_set(self):
        self._completed_session([
            {"reps": 8, "weight": "60.00"}, {"reps": 5, "weight": "80.00"}, {"reps": 3, "weight": "95.00"},
        ])
        data = self._start_program_session(target_sets=4)
        weights = [row["weight"] for row in data["exercises"][0]["sets"]]
        self.assertEqual(weights, ["60.00", "80.00", "95.00", "95.00"])

    def test_program_target_weight_is_used_until_the_exercise_has_history(self):
        data = self._start_program_session(target_weight="60.00")
        self.assertEqual(data["exercises"][0]["sets"][0]["weight"], "60.00")
        self.assertIsNone(data["exercises"][0]["last_performance"])

    def test_another_persons_training_never_prefills_this_session(self):
        other = Person.objects.create(
            household=get_active_household(), display_name="Housemate",
            created_by=self.user, updated_by=self.user,
        )
        self._completed_session([{"reps": 5, "weight": "140.00"}], person=other)
        data = self._start_program_session(target_weight="60.00")
        self.assertEqual(data["exercises"][0]["sets"][0]["weight"], "60.00")

    def test_private_history_still_prefills_for_the_person_who_trained(self):
        self._completed_session([{"reps": 5, "weight": "77.50"}], visibility="private")
        data = self._start_program_session(target_weight="60.00")
        self.assertEqual(data["exercises"][0]["sets"][0]["weight"], "77.50")

    def test_exercise_added_mid_session_prefills_from_history(self):
        self._completed_session([{"reps": 6, "weight": "45.00"}])
        response = self.client.post("/api/v1/fitness/sessions/start/", {
            "person_id": self.person.id, "name": "Open workout",
        }, format="json")
        response = self.client.post(f"/api/v1/fitness/sessions/{response.data['id']}/exercises/", {
            "exercise_id": self.exercise.id, "target_sets": 1,
        }, format="json")
        self.assertEqual(response.data["sets"][0]["weight"], "45.00")
        self.assertEqual(response.data["sets"][0]["reps"], 6)

    def test_added_set_repeats_the_set_just_completed(self):
        data = self._start_program_session(target_weight="70.00")
        entry_id = data["exercises"][0]["id"]
        self.client.patch(f"/api/v1/fitness/session-sets/{data['exercises'][0]['sets'][0]['id']}/", {
            "reps": 5, "weight": "72.50", "is_completed": True,
        }, format="json")
        response = self.client.post(f"/api/v1/fitness/session-exercises/{entry_id}/sets/", {}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["weight"], "72.50")
        self.assertEqual(response.data["reps"], 5)

    def test_abandoned_training_does_not_become_the_default_weight(self):
        response = self.client.post("/api/v1/fitness/sessions/start/", {
            "person_id": self.person.id, "name": "Cut short",
        }, format="json")
        session_id = response.data["id"]
        response = self.client.post(f"/api/v1/fitness/sessions/{session_id}/exercises/", {
            "exercise_id": self.exercise.id, "target_sets": 1,
        }, format="json")
        self.client.patch(f"/api/v1/fitness/session-sets/{response.data['sets'][0]['id']}/", {
            "reps": 1, "weight": "200.00", "is_completed": True,
        }, format="json")
        self.client.post(f"/api/v1/fitness/sessions/{session_id}/abandon/", {}, format="json")
        data = self._start_program_session(target_weight="60.00")
        self.assertEqual(data["exercises"][0]["sets"][0]["weight"], "60.00")

    def test_live_session_can_add_and_drop_exercise(self):
        response = self.client.post("/api/v1/fitness/sessions/start/", {
            "person_id": self.person.id, "name": "Flexible session",
        }, format="json")
        session_id = response.data["id"]
        response = self.client.post(f"/api/v1/fitness/sessions/{session_id}/exercises/", {
            "exercise_id": self.exercise.id, "target_sets": 2,
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(len(response.data["sets"]), 2)
        response = self.client.post(f"/api/v1/fitness/session-exercises/{response.data['id']}/drop/", {}, format="json")
        self.assertEqual(response.data["status"], "dropped")
