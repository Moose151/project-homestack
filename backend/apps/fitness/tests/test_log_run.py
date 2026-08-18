"""Quick run logging — one training history, not two.

The design rule these tests defend: a run logged through the quick form is an ordinary completed
WorkoutSession. If any of these start passing only because a parallel Run model appeared, the
feature has gone wrong.
"""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.fitness import services
from apps.fitness.models import (
    Exercise, PersonalRecord, SessionSet, WorkoutSession,
)
from apps.people.models import Person

LOG_RUN_URL = "/api/v1/fitness/sessions/log-run/"


def _user(username, role="admin"):
    return User.objects.create_user(
        username=username, display_name=username.title(), role=role, password="test-pass-123",
    )


def _person(user=None, name="Runner"):
    return Person.objects.create(
        household=get_active_household(), linked_user=user, display_name=name,
    )


class LogRunSessionShapeTests(TestCase):
    def setUp(self):
        self.user = _user("runner")
        self.person = _person(self.user)

    def _log(self, **overrides):
        payload = dict(
            person_id=self.person.id, distance="5.00", duration_seconds=28 * 60 + 14,
        )
        payload.update(overrides)
        return services.log_run(self.user, **payload)

    def test_a_run_is_an_ordinary_completed_session(self):
        session = self._log()
        self.assertEqual(session.status, WorkoutSession.Status.COMPLETED)
        self.assertIsNotNone(session.finished_at)
        # Ad-hoc: nobody had to build a training program to record a run.
        self.assertIsNone(session.program_id)
        self.assertIsNone(session.source_workout_id)

    def test_the_run_uses_a_distance_time_running_exercise(self):
        session = self._log()
        exercise = session.exercises.get().exercise
        # Classification, not display name — renaming the exercise must not break logging.
        self.assertEqual(exercise.exercise_type, Exercise.ExerciseType.RUNNING)
        self.assertEqual(exercise.measurement, Exercise.Measurement.DISTANCE_TIME)

    def test_distance_and_duration_persist(self):
        session = self._log(distance="5.00", duration_seconds=1694)
        workout_set = SessionSet.objects.get(session_exercise__session=session)
        self.assertEqual(workout_set.distance, Decimal("5.000"))
        self.assertEqual(workout_set.duration_seconds, 1694)
        self.assertTrue(workout_set.is_completed)
        self.assertEqual(session.duration_seconds, 1694)

    def test_a_past_run_keeps_its_own_duration_not_the_wall_clock_gap(self):
        yesterday = timezone.now() - timedelta(days=1)
        session = self._log(started_at=yesterday, duration_seconds=1800)
        self.assertEqual(session.duration_seconds, 1800)
        self.assertEqual(session.finished_at, yesterday + timedelta(seconds=1800))

    def test_notes_and_visibility_are_stored(self):
        session = self._log(notes="Easy pace", visibility="private")
        self.assertEqual(session.notes, "Easy pace")
        self.assertEqual(session.visibility, "private")

    def test_a_logged_run_appears_in_ordinary_session_history(self):
        session = self._log()
        from apps.fitness import selectors
        ids = [row.id for row in selectors.list_sessions(self.user)]
        self.assertIn(session.id, ids)


class LogRunValidationTests(TestCase):
    def setUp(self):
        self.user = _user("runner2")
        self.person = _person(self.user)

    def _log(self, **overrides):
        payload = dict(person_id=self.person.id, distance="5", duration_seconds=600)
        payload.update(overrides)
        return services.log_run(self.user, **payload)

    def test_zero_or_negative_distance_is_rejected(self):
        for distance in ("0", "-1", "-0.5"):
            with self.assertRaises(services.FitnessError, msg=distance):
                self._log(distance=distance)

    def test_zero_or_negative_duration_is_rejected(self):
        for duration in (0, -1, -600):
            with self.assertRaises(services.FitnessError, msg=duration):
                self._log(duration_seconds=duration)

    def test_malformed_numbers_are_rejected(self):
        with self.assertRaises(services.FitnessError):
            self._log(distance="not a number")
        with self.assertRaises(services.FitnessError):
            self._log(duration_seconds="soon")

    def test_absurd_values_are_rejected(self):
        with self.assertRaises(services.FitnessError):
            self._log(distance="5000")
        with self.assertRaises(services.FitnessError):
            self._log(duration_seconds=48 * 3600)

    def test_a_future_run_is_rejected(self):
        with self.assertRaises(services.FitnessError):
            self._log(started_at=timezone.now() + timedelta(days=1))


class LogRunPermissionTests(TestCase):
    """Logging for someone else follows the existing Fitness rule, not a new one."""

    def setUp(self):
        self.manager = _user("run-manager", role="manager")
        self.member = _user("run-member", role="user")
        self.other = _user("run-other", role="user")
        self.member_person = _person(self.member, "Member")
        self.other_person = _person(self.other, "Other")

    def test_a_member_can_log_their_own_run(self):
        session = services.log_run(
            self.member, person_id=self.member_person.id, distance="3", duration_seconds=900,
        )
        self.assertEqual(session.person_id, self.member_person.id)

    def test_a_member_cannot_log_for_someone_else(self):
        with self.assertRaises(services.FitnessError):
            services.log_run(
                self.member, person_id=self.other_person.id, distance="3", duration_seconds=900,
            )

    def test_a_manager_may_log_for_another_person(self):
        session = services.log_run(
            self.manager, person_id=self.member_person.id, distance="3", duration_seconds=900,
        )
        self.assertEqual(session.person_id, self.member_person.id)


class LogRunPersonalRecordTests(TestCase):
    """Runs must earn records through the same path a normal session uses."""

    def setUp(self):
        self.user = _user("pb-runner")
        self.person = _person(self.user)

    def _log(self, distance, duration_seconds, **extra):
        return services.log_run(
            self.user, person_id=self.person.id, distance=distance,
            duration_seconds=duration_seconds, **extra,
        )

    def test_a_run_sets_longest_distance_and_fastest_time(self):
        self._log("5.00", 1800)
        kinds = set(
            PersonalRecord.objects.filter(person=self.person).values_list("kind", flat=True)
        )
        self.assertIn(PersonalRecord.Kind.LONGEST_DISTANCE, kinds)
        self.assertIn(PersonalRecord.Kind.FASTEST_TIME, kinds)

    def test_a_longer_run_improves_the_distance_record(self):
        self._log("5.00", 1800)
        self._log("10.00", 3900)
        record = PersonalRecord.objects.get(
            person=self.person, kind=PersonalRecord.Kind.LONGEST_DISTANCE,
        )
        self.assertEqual(record.value, Decimal("10.000"))

    def test_fastest_time_is_kept_per_distance(self):
        """5 km and 10 km are separate records, as the existing model already intends."""
        self._log("5.00", 1800)
        self._log("10.00", 3900)
        distances = set(
            PersonalRecord.objects.filter(
                person=self.person, kind=PersonalRecord.Kind.FASTEST_TIME,
            ).values_list("distance", flat=True)
        )
        self.assertEqual(distances, {Decimal("5.000"), Decimal("10.000")})

    def test_a_faster_run_at_the_same_distance_improves_the_record(self):
        self._log("5.00", 1800)
        self._log("5.00", 1500)
        record = PersonalRecord.objects.get(
            person=self.person, kind=PersonalRecord.Kind.FASTEST_TIME,
            distance=Decimal("5.000"),
        )
        self.assertEqual(record.value, Decimal("1500"))

    def test_a_slower_run_does_not_replace_the_record(self):
        self._log("5.00", 1500)
        self._log("5.00", 1800)
        record = PersonalRecord.objects.get(
            person=self.person, kind=PersonalRecord.Kind.FASTEST_TIME,
            distance=Decimal("5.000"),
        )
        self.assertEqual(record.value, Decimal("1500"))

    def test_the_quick_flow_and_the_ordinary_session_path_earn_the_same_record(self):
        """The regression that proves there is only one records mechanism."""
        from apps.fitness.models import SessionExercise

        # The long way round: start, add exercise, complete a set, finish.
        exercise = Exercise.objects.filter(
            exercise_type=Exercise.ExerciseType.RUNNING,
            measurement=Exercise.Measurement.DISTANCE_TIME,
        ).first()
        session = services.start_session(self.user, person_id=self.person.id, name="Manual run")
        entry = services.add_session_exercise(self.user, session, exercise_id=exercise.id)
        workout_set = SessionSet.objects.filter(session_exercise=entry).first()
        services.update_set(
            self.user, workout_set, distance="7.00", duration_seconds=2400, is_completed=True,
        )
        services.finish_session(self.user, session)
        long_way = PersonalRecord.objects.get(
            person=self.person, kind=PersonalRecord.Kind.LONGEST_DISTANCE,
        )
        self.assertEqual(long_way.value, Decimal("7.000"))

        # The quick way, beating it. Same record row, same mechanism.
        self._log("9.00", 3000)
        quick_way = PersonalRecord.objects.get(
            person=self.person, kind=PersonalRecord.Kind.LONGEST_DISTANCE,
        )
        self.assertEqual(quick_way.pk, long_way.pk)
        self.assertEqual(quick_way.value, Decimal("9.000"))


class LogRunSocialTests(TestCase):
    def setUp(self):
        self.user = _user("social-runner")
        self.other = _user("social-watcher", role="user")
        self.person = _person(self.user)

    def test_a_household_run_notifies_others_like_any_workout(self):
        from apps.notifications.models import Notification

        services.log_run(
            self.user, person_id=self.person.id, distance="5", duration_seconds=1800,
            visibility="household",
        )
        self.assertTrue(
            Notification.objects.filter(recipient_user=self.other, source_node="fitness").exists()
        )

    def test_a_private_run_does_not_reach_the_household(self):
        from apps.notifications.models import Notification

        services.log_run(
            self.user, person_id=self.person.id, distance="5", duration_seconds=1800,
            visibility="private",
        )
        self.assertFalse(
            Notification.objects.filter(recipient_user=self.other, source_node="fitness").exists()
        )


class LogRunApiTests(TestCase):
    def setUp(self):
        self.user = _user("api-runner")
        self.person = _person(self.user)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_endpoint_creates_a_run(self):
        response = self.client.post(LOG_RUN_URL, {
            "person_id": self.person.id, "distance": "5.00", "duration_seconds": 1694,
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], "completed")

    def test_endpoint_rejects_invalid_input(self):
        for payload in (
            {"person_id": self.person.id, "distance": "0", "duration_seconds": 600},
            {"person_id": self.person.id, "distance": "5", "duration_seconds": 0},
            {"person_id": self.person.id, "distance": "-5", "duration_seconds": 600},
            {"person_id": self.person.id, "duration_seconds": 600},
        ):
            self.assertEqual(
                self.client.post(LOG_RUN_URL, payload, format="json").status_code, 400, payload,
            )

    def test_anonymous_cannot_log_a_run(self):
        client = APIClient()
        self.assertEqual(
            client.post(LOG_RUN_URL, {
                "person_id": self.person.id, "distance": "5", "duration_seconds": 600,
            }, format="json").status_code, 403,
        )

    def test_a_completed_run_is_immutable_like_any_finished_session(self):
        response = self.client.post(LOG_RUN_URL, {
            "person_id": self.person.id, "distance": "5", "duration_seconds": 600,
        }, format="json")
        session = WorkoutSession.objects.get(pk=response.data["id"])
        workout_set = SessionSet.objects.get(session_exercise__session=session)
        with self.assertRaises(services.FitnessError):
            services.update_set(self.user, workout_set, distance="99")
