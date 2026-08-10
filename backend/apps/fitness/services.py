from decimal import Decimal

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
def finish_session(user, session, *, notes=None):
    _active_session(session)
    _validate_session_access(user, session)
    now = timezone.now()
    if notes is not None:
        session.notes = notes
    session.status = WorkoutSession.Status.COMPLETED
    session.finished_at = now
    session.duration_seconds = max(0, int((now - session.started_at).total_seconds()))
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
                action_url=f"/fitness?session={session.id}",
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
