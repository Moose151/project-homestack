from apps.meridian.models import MeridianTask, MeridianTaskCompletion, MeridianWishlistItem
from apps.people.corner_registry import register
from apps.permissions.visibility import apply_visibility


def provide(*, user, person, since):
    visible_tasks = apply_visibility(MeridianTask.objects.all(), user)
    assignments = [{
        "key": f"meridian:task:{row.id}", "source_node": "meridian", "kind": "task",
        "title": row.title, "summary": f"{row.points} points", 
        "due_at": row.due_at.isoformat() if row.due_at else None,
        "action_url": "/meridian?tab=tasks",
    } for row in visible_tasks.filter(
        assigned_to_people=person, is_active=True, is_archived=False
    ).exclude(status="approved")]
    completions = MeridianTaskCompletion.objects.filter(
        person=person, task_id__in=visible_tasks.values_list("id", flat=True),
        submitted_at__gte=since,
    ).select_related("task")
    activity = [{
        "key": f"meridian:completion:{row.id}:{row.status}", "source_node": "meridian",
        "kind": "task_completion", "title": f"Completed {row.task.title}",
        "summary": row.get_status_display(), "occurred_at": row.submitted_at.isoformat(),
        "action_url": "/meridian?tab=tasks",
    } for row in completions]
    collections = [{
        "key": f"meridian:wish:{row.id}", "source_node": "meridian", "kind": "meridian_wish",
        "title": row.name, "summary": f"{row.progress_percentage()}% funded",
        "action_url": "/meridian?tab=wishlist",
    } for row in MeridianWishlistItem.objects.filter(person=person, is_active=True)]
    return {"activity": activity, "assignments": assignments, "collections": collections}


register("meridian", provide)
