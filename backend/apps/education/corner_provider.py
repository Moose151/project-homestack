from apps.education.models import EducationAssessment
from apps.people.corner_registry import register
from apps.permissions.visibility import apply_visibility


def provide(*, user, person, since):
    rows = apply_visibility(EducationAssessment.objects.filter(assigned_to_people=person), user)
    assignments = [{
        "key": f"education:assessment:{row.id}", "source_node": "education", "kind": "assessment",
        "title": row.title, "summary": row.get_status_display(),
        "due_at": row.due_at.isoformat() if row.due_at else None,
        "action_url": f"/education?tab=assignments&assessment={row.id}",
    } for row in rows.exclude(status__in=["submitted", "done"])]
    activity = [{
        "key": f"education:assessment:{row.id}:{row.status}", "source_node": "education",
        "kind": "assessment_completion", "title": f"Finished {row.title}",
        "summary": row.get_status_display(), "occurred_at": row.updated_at.isoformat(),
        "action_url": f"/education?tab=assignments&assessment={row.id}",
    } for row in rows.filter(status__in=["submitted", "done"], updated_at__gte=since)]
    return {"activity": activity, "assignments": assignments, "collections": []}


register("education", provide)
