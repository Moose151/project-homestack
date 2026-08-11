from apps.fitness.models import PersonalRecord, ProgramAssignment, TrainingProgram, WorkoutSession
from apps.people.corner_registry import register
from apps.permissions.visibility import apply_visibility


def provide(*, user, person, since):
    visible_program_ids = apply_visibility(TrainingProgram.objects.all(), user).values_list("id", flat=True)
    programs = ProgramAssignment.objects.filter(
        person=person, is_active=True, program__is_archived=False, program_id__in=visible_program_ids,
    ).select_related("program")
    assignments = [{
        "key": f"fitness:program:{row.program_id}", "source_node": "fitness", "kind": "program",
        "title": row.program.name, "summary": "Training program", "due_at": None,
        "action_url": f"/fitness?tab=programs&program={row.program_id}",
    } for row in programs]
    sessions = apply_visibility(
        WorkoutSession.objects.filter(person=person, status="completed", finished_at__gte=since)
        .prefetch_related("exercises__exercise", "exercises__sets"), user
    )
    activity = [{
        "key": f"fitness:session:{row.id}:completed", "source_node": "fitness", "kind": "workout",
        "title": f"Completed {row.name}",
        "summary": f"{row.total_reps} reps · {row.duration_seconds // 60 if row.duration_seconds else 0} min",
        "occurred_at": (row.finished_at or row.started_at).isoformat(),
        "action_url": f"/fitness?tab=history&session={row.id}",
        "detail_summary": {
            "duration_seconds": row.duration_seconds,
            "total_reps": row.total_reps,
            "total_volume": str(row.total_volume),
            "exercises": [{
                "name": entry.exercise.name,
                "weight_unit": entry.exercise.weight_unit,
                "distance_unit": entry.exercise.distance_unit,
                "sets": [{
                    "reps": workout_set.reps,
                    "weight": None if workout_set.weight is None else str(workout_set.weight),
                    "duration_seconds": workout_set.duration_seconds,
                    "distance": str(workout_set.distance),
                } for workout_set in entry.sets.all() if workout_set.is_completed],
            } for entry in row.exercises.all() if entry.status == "active"],
        },
    } for row in sessions]
    visible_session_ids = apply_visibility(
        WorkoutSession.objects.filter(person=person), user,
    ).values_list("id", flat=True)
    records = PersonalRecord.objects.filter(
        person=person, session_id__in=visible_session_ids, achieved_at__gte=since,
    ).select_related("exercise")
    activity.extend({
        "key": f"fitness:record:{row.id}:{row.kind}", "source_node": "fitness",
        "kind": "personal_record", "title": f"Set a new {row.get_kind_display().lower()}",
        "summary": f"{row.exercise.name} · {row.value:g} {_record_unit(row)}".strip(),
        "occurred_at": row.achieved_at.isoformat(),
        "action_url": f"/fitness?tab=history&session={row.session_id}",
    } for row in records)
    return {"activity": activity, "assignments": assignments, "collections": []}


def _record_unit(record: PersonalRecord) -> str:
    if record.kind in {PersonalRecord.Kind.MAX_WEIGHT, PersonalRecord.Kind.ESTIMATED_1RM}:
        return record.exercise.weight_unit
    if record.kind == PersonalRecord.Kind.MAX_REPS:
        return "reps"
    if record.kind == PersonalRecord.Kind.FASTEST_TIME:
        return "seconds"
    return record.exercise.distance_unit


register("fitness", provide)
