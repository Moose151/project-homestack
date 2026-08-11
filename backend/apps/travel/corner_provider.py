from apps.people.corner_registry import register
from apps.permissions.visibility import apply_visibility
from apps.travel.models import TravelIdea, Trip


def provide(*, user, person, since):
    ideas = apply_visibility(TravelIdea.objects.filter(created_by=person.linked_user, created_at__gte=since), user) if person.linked_user_id else TravelIdea.objects.none()
    activity = [{
        "key": f"travel:idea:{row.id}:created", "source_node": "travel", "kind": "destination",
        "title": f"Added {row.title} to To go", "summary": row.destination,
        "occurred_at": row.created_at.isoformat(), "action_url": f"/travel?tab=ideas&idea={row.id}",
    } for row in ideas]
    trips = apply_visibility(Trip.objects.filter(participants=person).exclude(status__in=["completed", "cancelled"]), user)
    assignments = [{
        "key": f"travel:trip:{row.id}", "source_node": "travel", "kind": "trip",
        "title": row.title, "summary": row.destination,
        "due_at": row.start_date.isoformat() if row.start_date else None,
        "action_url": f"/travel?trip={row.id}",
    } for row in trips]
    return {"activity": activity, "assignments": assignments, "collections": []}


register("travel", provide)
