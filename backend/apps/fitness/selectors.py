from django.db import connection
from django.db.models import Q

from apps.fitness.models import (
    Exercise, PersonalRecord, SessionExercise, SessionSet, TrainingProgram, WorkoutSession,
)
from apps.permissions.visibility import apply_visibility


def list_exercises(user, *, query="", exercise_type="", muscle_group="", include_archived=False):
    qs = Exercise.objects.all()
    if not include_archived:
        qs = qs.filter(is_archived=False)
    if exercise_type:
        qs = qs.filter(exercise_type=exercise_type)
    if muscle_group:
        qs = qs.filter(muscle_group__iexact=muscle_group)
    if query:
        if connection.vendor == "postgresql":
            from django.contrib.postgres.search import SearchQuery, SearchVector
            qs = qs.annotate(_search=SearchVector("name", "muscle_group", "notes")).filter(_search=SearchQuery(query))
        else:
            qs = qs.filter(Q(name__icontains=query) | Q(muscle_group__icontains=query) | Q(notes__icontains=query))
    return list(qs.order_by("name"))


def get_exercise(pk):
    return Exercise.objects.filter(pk=pk).first()


def list_programs(user, *, assigned_person_id=None, include_archived=False):
    qs = TrainingProgram.objects.prefetch_related(
        "assignments__person", "workouts__exercises__exercise"
    )
    if not include_archived:
        qs = qs.filter(is_archived=False)
    if assigned_person_id:
        qs = qs.filter(assignments__person_id=assigned_person_id, assignments__is_active=True)
    return list(apply_visibility(qs.distinct(), user))


def get_program(user, pk):
    qs = apply_visibility(TrainingProgram.objects.prefetch_related(
        "assignments__person", "workouts__exercises__exercise"
    ), user)
    return qs.filter(pk=pk).first()


def list_sessions(user, *, person_id=None, status="", limit=100):
    qs = WorkoutSession.objects.select_related("person", "program").prefetch_related(
        "exercises__exercise", "exercises__sets", "personal_records"
    )
    qs = apply_visibility(qs, user)
    if person_id:
        qs = qs.filter(person_id=person_id)
    if status:
        qs = qs.filter(status=status)
    return attach_last_performance(user, list(qs[:limit]))


def get_session(user, pk):
    qs = apply_visibility(WorkoutSession.objects.select_related("person", "program").prefetch_related(
        "exercises__exercise", "exercises__sets", "personal_records"
    ), user)
    session = qs.filter(pk=pk).first()
    if session:
        attach_last_performance(user, [session])
    return session


def last_performance(user, person_id, exercise_ids):
    """What the person actually completed the previous time they trained each exercise.

    Returns `{exercise_id: {"session_id", "session_name", "performed_at", "sets": [...]}}`, where
    the sets come from that exercise's most recent completed session in set order. Sessions are
    visibility-filtered, so a private session never prefills or informs someone else's screen.
    """
    exercise_ids = [pk for pk in dict.fromkeys(exercise_ids or []) if pk]
    if not person_id or not exercise_ids:
        return {}
    sessions = apply_visibility(
        WorkoutSession.objects.filter(person_id=person_id, status=WorkoutSession.Status.COMPLETED),
        user,
    )
    rows = SessionSet.objects.filter(
        session_exercise__session__in=sessions,
        session_exercise__status=SessionExercise.Status.ACTIVE,
        session_exercise__exercise_id__in=exercise_ids,
        is_completed=True,
    ).select_related("session_exercise__session").order_by(
        "session_exercise__exercise_id", "-session_exercise__session__started_at", "position", "id",
    )
    history = {}
    for row in rows:
        exercise_id = row.session_exercise.exercise_id
        session = row.session_exercise.session
        entry = history.get(exercise_id)
        if entry is None:
            entry = history[exercise_id] = {
                "session_id": session.id, "session_name": session.name,
                "performed_at": session.finished_at or session.started_at, "sets": [],
            }
        elif entry["session_id"] != session.id:
            continue  # Ordering means we have moved on to an older session for this exercise.
        entry["sets"].append({
            "reps": row.reps, "weight": row.weight,
            "duration_seconds": row.duration_seconds, "distance": row.distance,
        })
    return history


def previous_set(history_entry, index):
    """The set performed at the same position last time, falling back to the final set."""
    sets = (history_entry or {}).get("sets") or []
    if not sets:
        return {}
    return sets[index] if index < len(sets) else sets[-1]


def attach_last_performance(user, sessions):
    """Hang last-time history on the exercises of active sessions so the live screen can show it."""
    for session in sessions:
        if session.status != WorkoutSession.Status.ACTIVE:
            continue
        entries = list(session.exercises.all())
        history = last_performance(user, session.person_id, [entry.exercise_id for entry in entries])
        for entry in entries:
            entry.last_performance = history.get(entry.exercise_id)
    return sessions


def list_records(user, *, person_id=None, exercise_id=None):
    qs = PersonalRecord.objects.select_related("person", "exercise", "session")
    if person_id:
        qs = qs.filter(person_id=person_id)
    if exercise_id:
        qs = qs.filter(exercise_id=exercise_id)
    # A record is visible when its source session is visible.
    visible_sessions = apply_visibility(WorkoutSession.objects.all(), user).values("id")
    return list(qs.filter(session_id__in=visible_sessions))


def search_fitness(user, query):
    exercises = list_exercises(user, query=query)[:20]
    programs = apply_visibility(TrainingProgram.objects.all(), user).filter(
        Q(name__icontains=query) | Q(description__icontains=query)
    )[:20]
    sessions = apply_visibility(WorkoutSession.objects.select_related("person"), user).filter(
        Q(name__icontains=query) | Q(person__display_name__icontains=query)
    )[:20]
    return {"exercises": exercises, "programs": list(programs), "sessions": list(sessions)}
