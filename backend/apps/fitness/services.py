from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.fitness import events, selectors
from apps.fitness.models import (
    Exercise, PersonalRecord, ProgramAssignment, ProgramWorkout, SessionExercise,
    SessionSet, TrainingProgram, WorkoutExercise, WorkoutSession,
)
from apps.notifications import services as notifications
from apps.notifications.models import Notification
from apps.permissions.resolver import resolve_permission
from apps.people.models import Person


class FitnessError(ValueError):
    pass


def _base(user):
    return {"household": get_active_household(), "created_by": user, "updated_by": user}


def create_exercise(user, **data):
    obj = Exercise(**_base(user), **data)
    obj.save()
    return obj


def update_exercise(user, obj, **data):
    for key in ("name", "exercise_type", "muscle_group", "measurement", "weight_unit", "distance_unit", "is_archived", "notes"):
        if key in data:
            setattr(obj, key, data[key])
    obj.updated_by = user
    obj.save()
    return obj


def delete_exercise(user, obj):
    if obj.session_entries.exists() or obj.workout_templates.exists():
        obj.is_archived = True
        obj.updated_by = user
        obj.save()
    else:
        obj.soft_delete()


def _validate_person(person_id):
    person = Person.objects.filter(pk=person_id).first()
    if not person:
        raise FitnessError("The selected person does not exist.")
    return person


def _validate_subject_access(user, person):
    if user.role not in ("admin", "manager") and person.linked_user_id != user.id:
        raise FitnessError("You can only log or assign training for your own profile.")


def _validate_program_access(user, program):
    if user.role not in ("admin", "manager") and program.created_by_id != user.id:
        raise FitnessError("Only the program owner or a manager can change this program.")


def _validate_session_access(user, session):
    if user.role not in ("admin", "manager") and session.person.linked_user_id != user.id:
        raise FitnessError("You can only change your own workout.")


def _validate_exercise(exercise_id):
    exercise = Exercise.objects.filter(pk=exercise_id, is_archived=False).first()
    if not exercise:
        raise FitnessError("The selected exercise does not exist or is archived.")
    return exercise


@transaction.atomic
def create_program(user, *, workouts=None, person_ids=None, **data):
    obj = TrainingProgram(**_base(user), **data)
    obj.save()
    _replace_program_contents(user, obj, workouts or [], person_ids or [])
    return obj


@transaction.atomic
def update_program(user, obj, *, workouts=None, person_ids=None, **data):
    _validate_program_access(user, obj)
    for key in ("name", "description", "visibility", "is_archived"):
        if key in data:
            setattr(obj, key, data[key])
    obj.updated_by = user
    obj.save()
    if workouts is not None or person_ids is not None:
        existing_workouts = workouts if workouts is not None else [
            {"name": w.name, "position": w.position, "notes": w.notes, "exercises": [
                {k: getattr(e, k) for k in ("exercise_id", "position", "target_sets", "target_reps", "target_weight", "target_duration_seconds", "target_distance", "rest_seconds", "notes")}
                for e in w.exercises.all()
            ]} for w in obj.workouts.all()
        ]
        existing_people = person_ids if person_ids is not None else list(obj.assignments.filter(is_active=True).values_list("person_id", flat=True))
        _replace_program_contents(user, obj, existing_workouts, existing_people)
    return obj


def _replace_program_contents(user, program, workouts, person_ids):
    # Templates are replaceable configuration. Sessions retain immutable snapshots and the
    # nullable source links intentionally clear when an old template is replaced.
    program.workouts.all().delete()
    program.assignments.all().delete()
    for workout_data in workouts:
        exercises = workout_data.pop("exercises", [])
        workout = ProgramWorkout(program=program, **_base(user), **workout_data)
        workout.save()
        for exercise_data in exercises:
            _validate_exercise(exercise_data["exercise_id"])
            WorkoutExercise(workout=workout, **_base(user), **exercise_data).save()
    for person_id in dict.fromkeys(person_ids):
        person = _validate_person(person_id)
        _validate_subject_access(user, person)
        ProgramAssignment(program=program, person=person, **_base(user)).save()


def delete_program(user, obj):
    _validate_program_access(user, obj)
    obj.updated_by = user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


@transaction.atomic
def start_session(user, *, person_id, workout_id=None, name="", visibility="household"):
    person = _validate_person(person_id)
    _validate_subject_access(user, person)
    workout = None
    if workout_id:
        workout = ProgramWorkout.objects.select_related("program").prefetch_related("exercises__exercise").filter(pk=workout_id).first()
        if not workout:
            raise FitnessError("The selected workout does not exist.")
        if not workout.program.assignments.filter(person_id=person_id, is_active=True).exists() and user.role not in ("admin", "manager"):
            raise FitnessError("This program is not assigned to that person.")
    session = WorkoutSession(
        person=person, program=workout.program if workout else None, source_workout=workout,
        name=name or (workout.name if workout else "Workout"), started_at=timezone.now(),
        visibility=visibility, **_base(user),
    )
    session.save()
    if workout:
        templates = list(workout.exercises.all())
        history = selectors.last_performance(user, person.id, [t.exercise_id for t in templates])
        for template in templates:
            entry = SessionExercise(
                session=session, exercise=template.exercise, source_template=template,
                position=template.position, notes=template.notes, **_base(user),
            )
            entry.save()
            last_time = history.get(template.exercise_id)
            for position in range(template.target_sets):
                previous = selectors.previous_set(last_time, position)
                SessionSet(
                    session_exercise=entry, position=position,
                    reps=template.target_reps if template.target_reps is not None else previous.get("reps"),
                    # What the person actually lifted last time beats a program target that
                    # stopped being current the moment they progressed past it.
                    weight=previous.get("weight") if previous.get("weight") is not None else template.target_weight,
                    duration_seconds=template.target_duration_seconds,
                    distance=template.target_distance or 0, **_base(user),
                ).save()
    return session


def _active_session(session):
    if session.status != WorkoutSession.Status.ACTIVE:
        raise FitnessError("This workout is no longer active.")


def add_session_exercise(user, session, *, exercise_id, target_sets=1, **data):
    _active_session(session)
    _validate_session_access(user, session)
    exercise = _validate_exercise(exercise_id)
    position = session.exercises.count()
    entry = SessionExercise(session=session, exercise=exercise, position=position, notes=data.get("notes", ""), **_base(user))
    entry.save()
    entry.last_performance = selectors.last_performance(user, session.person_id, [exercise.id]).get(exercise.id)
    for index in range(max(1, target_sets)):
        previous = selectors.previous_set(entry.last_performance, index)
        SessionSet(
            session_exercise=entry, position=index, reps=previous.get("reps"),
            weight=previous.get("weight"), distance=previous.get("distance") or 0, **_base(user),
        ).save()
    return entry


def drop_session_exercise(user, entry):
    _active_session(entry.session)
    _validate_session_access(user, entry.session)
    entry.status = SessionExercise.Status.DROPPED
    entry.updated_by = user
    entry.save()
    return entry


def add_set(user, entry):
    _active_session(entry.session)
    _validate_session_access(user, entry.session)
    existing = list(entry.sets.all())
    # An extra set continues this workout, so it repeats the set just done; only when the
    # exercise has no sets yet does last time's training supply the starting weight.
    if existing:
        previous = {"reps": existing[-1].reps, "weight": existing[-1].weight, "distance": existing[-1].distance}
    else:
        history = selectors.last_performance(user, entry.session.person_id, [entry.exercise_id])
        previous = selectors.previous_set(history.get(entry.exercise_id), 0)
    obj = SessionSet(
        session_exercise=entry, position=len(existing), reps=previous.get("reps"),
        weight=previous.get("weight"), distance=previous.get("distance") or 0, **_base(user),
    )
    obj.save()
    return obj


def update_set(user, obj, **data):
    _active_session(obj.session_exercise.session)
    _validate_session_access(user, obj.session_exercise.session)
    for key in ("reps", "weight", "duration_seconds", "distance", "is_completed"):
        if key in data:
            setattr(obj, key, data[key])
    obj.completed_at = timezone.now() if obj.is_completed else None
    obj.updated_by = user
    obj.save()
    return obj


def _record_candidate(person, exercise, session, workout_set, kind, value, distance=Decimal("0"), lower_is_better=False):
    if value is None or value <= 0:
        return None
    current = PersonalRecord.objects.filter(person=person, exercise=exercise, kind=kind, distance=distance).first()
    improved = current is None or (value < current.value if lower_is_better else value > current.value)
    if not improved:
        return None
    fields = dict(session=session, session_set=workout_set, value=value, achieved_at=session.finished_at, updated_by=session.updated_by)
    if current:
        for key, val in fields.items():
            setattr(current, key, val)
        current.save()
        record = current
    else:
        record = PersonalRecord(
            person=person, exercise=exercise, kind=kind, distance=distance,
            household=get_active_household(), created_by=session.updated_by, **fields,
        )
        record.save()
    events.personal_record_set(record.id, record.household_id, person.id)
    return record


@transaction.atomic
def finish_session(user, session, *, notes=None, finished_at=None, duration_seconds=None):
    """Complete a session, derive personal records, notify and emit the Corner event.

    ``finished_at``/``duration_seconds`` exist for entries logged after the fact — a run
    recorded this evening for this morning must keep its own duration rather than the wall-clock
    gap since the row was created. Both default to the live behaviour, so an ordinary workout
    finishes exactly as it always has. There is deliberately only one finish path: personal
    records, notifications and social events are derived here and nowhere else.
    """
    _active_session(session)
    _validate_session_access(user, session)
    now = finished_at or timezone.now()
    if notes is not None:
        session.notes = notes
    session.status = WorkoutSession.Status.COMPLETED
    session.finished_at = now
    session.duration_seconds = (
        duration_seconds
        if duration_seconds is not None
        else max(0, int((now - session.started_at).total_seconds()))
    )
    completed_sets = SessionSet.objects.select_related("session_exercise__exercise").filter(
        session_exercise__session=session, session_exercise__status=SessionExercise.Status.ACTIVE,
        is_completed=True,
    )
    session.total_reps = sum(s.reps or 0 for s in completed_sets)
    session.total_volume = sum((Decimal(s.reps or 0) * (s.weight or Decimal("0"))) for s in completed_sets)
    session.updated_by = user
    session.save()
    records = []
    for workout_set in completed_sets:
        exercise = workout_set.session_exercise.exercise
        if workout_set.weight:
            records.append(_record_candidate(session.person, exercise, session, workout_set, PersonalRecord.Kind.MAX_WEIGHT, workout_set.weight))
            if workout_set.reps and workout_set.reps <= 12:
                estimated = workout_set.weight * (Decimal("1") + Decimal(workout_set.reps) / Decimal("30"))
                records.append(_record_candidate(session.person, exercise, session, workout_set, PersonalRecord.Kind.ESTIMATED_1RM, estimated))
        if workout_set.reps:
            records.append(_record_candidate(session.person, exercise, session, workout_set, PersonalRecord.Kind.MAX_REPS, Decimal(workout_set.reps)))
        if workout_set.distance:
            records.append(_record_candidate(session.person, exercise, session, workout_set, PersonalRecord.Kind.LONGEST_DISTANCE, workout_set.distance))
            if workout_set.duration_seconds:
                records.append(_record_candidate(session.person, exercise, session, workout_set, PersonalRecord.Kind.FASTEST_TIME, Decimal(workout_set.duration_seconds), workout_set.distance, True))
    records = [record for record in records if record]
    message = f"{session.person.name} completed {session.name} in {session.duration_seconds // 60} minutes."
    if records:
        message += f" {len(records)} new personal record{'s' if len(records) != 1 else ''}!"
    for recipient in User.objects.filter(is_active=True).exclude(pk=user.pk):
        if session.visibility == "household" and resolve_permission(recipient, "view", "fitness"):
            notifications.create_notification(
                recipient, title="Workout completed", message=message,
                level=Notification.Level.SUCCESS, source_node="fitness",
                action_url=f"/fitness?tab=history&session={session.id}",
                category="fitness",
            )
    events.session_completed(session.id, session.household_id, session.person_id, len(records))
    return session


def abandon_session(user, session):
    _active_session(session)
    _validate_session_access(user, session)
    session.status = WorkoutSession.Status.ABANDONED
    session.finished_at = timezone.now()
    session.duration_seconds = max(0, int((session.finished_at - session.started_at).total_seconds()))
    session.updated_by = user
    session.save()
    return session


# ---------------------------------------------------------------------------
# Quick run logging
# ---------------------------------------------------------------------------

# The run is recorded against a real distance/time exercise so it behaves like any other
# training entry. Matched on the stable classification (exercise_type + measurement), never on a
# display name — renaming "Running" must not break run logging.
RUN_EXERCISE_NAME = "Running"


def _run_exercise():
    """The household's running exercise, created once if it is somehow absent.

    0002_seed_common_exercises ships one, so this normally just finds it. Creating a fallback
    rather than failing means a household that archived or renamed every running exercise can
    still log a run.
    """
    exercise = (
        Exercise.objects.filter(
            exercise_type=Exercise.ExerciseType.RUNNING,
            measurement=Exercise.Measurement.DISTANCE_TIME,
            is_archived=False,
        )
        .order_by("id")
        .first()
    )
    if exercise is not None:
        return exercise
    exercise = Exercise(
        household=get_active_household(),
        name=RUN_EXERCISE_NAME,
        exercise_type=Exercise.ExerciseType.RUNNING,
        measurement=Exercise.Measurement.DISTANCE_TIME,
        muscle_group="Full body",
        is_system=True,
    )
    exercise.save()
    return exercise


@transaction.atomic
def log_run(user, *, person_id, distance, duration_seconds, started_at=None,
            notes="", visibility="household"):
    """Record a completed run as an ordinary Fitness session.

    Deliberately not a separate Run model. A run logged here is a normal completed
    WorkoutSession holding one distance/time exercise and one completed set, so it takes part in
    history, personal records, permissions, notifications and Corner activity through exactly
    the same code as a workout — there is one training history, not two.

    ``program`` stays null: WorkoutSession already allows an ad-hoc session, so nobody has to
    invent a training program merely to record a run.
    """
    person = _validate_person(person_id)
    # The same rule as every other Fitness write: you log for yourself unless you manage.
    _validate_subject_access(user, person)

    try:
        distance = Decimal(str(distance))
    except (InvalidOperation, TypeError, ValueError):
        raise FitnessError("Enter the distance you ran.")
    if distance <= 0:
        raise FitnessError("Distance must be greater than zero.")
    if distance > Decimal("1000"):
        raise FitnessError("That distance looks wrong — check the number.")

    try:
        duration_seconds = int(duration_seconds)
    except (TypeError, ValueError):
        raise FitnessError("Enter how long the run took.")
    if duration_seconds <= 0:
        raise FitnessError("Duration must be greater than zero.")
    if duration_seconds > 24 * 3600:
        raise FitnessError("That duration looks wrong — check the time.")

    started_at = started_at or timezone.now()
    if started_at > timezone.now():
        raise FitnessError("A run cannot be logged in the future.")

    exercise = _run_exercise()
    session = WorkoutSession(
        person=person,
        program=None,
        source_workout=None,
        name="Run",
        started_at=started_at,
        visibility=visibility,
        **_base(user),
    )
    session.save()
    entry = SessionExercise(session=session, exercise=exercise, position=0, **_base(user))
    entry.save()
    SessionSet(
        session_exercise=entry,
        position=0,
        distance=distance,
        duration_seconds=duration_seconds,
        is_completed=True,
        completed_at=started_at,
        **_base(user),
    ).save()

    # The shared finish path: personal records, notifications and the Corner event all come from
    # here, so a quick-logged run earns the same records as the long way round.
    return finish_session(
        user,
        session,
        notes=notes,
        finished_at=started_at + timedelta(seconds=duration_seconds),
        duration_seconds=duration_seconds,
    )
