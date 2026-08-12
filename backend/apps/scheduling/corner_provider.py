"""Calendar projection for a person's Corner.

The Calendar had no Corner provider at all, so a shared household calendar — arguably the most
visible thing anyone adds to — contributed nothing to either half of a Corner: adding an event
never appeared in recent activity, and an appointment assigned to someone never appeared under
their assignments.

Only standalone calendar events are projected. Synced events belong to the node that owns the
record (an Atlas to-do, an education class), and those nodes already project their own — showing
the mirrored CalendarEvent too would list the same thing twice in one Corner.
"""
from apps.people.corner_registry import register
from apps.permissions.visibility import apply_visibility
from apps.scheduling.models import CalendarEvent

# Anything the household is unlikely to think of as "someone added this": birthdays are derived
# from People, and holidays are imported rather than authored.
_ACTIVITY_EXCLUDED_KINDS = {CalendarEvent.EventKind.BIRTHDAY, CalendarEvent.EventKind.HOLIDAY}


def _action_url(event: CalendarEvent) -> str:
    date = event.start_at.date().isoformat() if event.start_at else ""
    return f"/calendar?date={date}&event={event.id}" if date else f"/calendar?event={event.id}"


def provide(*, user, person, since):
    # Standalone events only, and only the ones this viewer is allowed to see — a private or
    # surprise-hidden event must not surface through someone's Corner (D10).
    visible = apply_visibility(
        CalendarEvent.objects.filter(source_record_id__isnull=True), user,
    )

    assignments = [
        {
            "key": f"scheduling:event:{row.id}",
            "source_node": "scheduling",
            "kind": row.event_kind,
            "title": row.title,
            "summary": row.location or "",
            "due_at": row.start_at.isoformat() if row.start_at else None,
            "action_url": _action_url(row),
        }
        for row in visible.filter(assigned_to_people=person).order_by("start_at")
    ]

    activity = []
    if person.linked_user_id:
        created = (
            visible.filter(created_by_id=person.linked_user_id, created_at__gte=since)
            .exclude(event_kind__in=_ACTIVITY_EXCLUDED_KINDS)
            .order_by("-created_at")
        )
        activity = [
            {
                "key": f"scheduling:event:{row.id}:created",
                "source_node": "scheduling",
                "kind": "created",
                "title": f"Added {row.title}",
                "summary": row.location or "",
                "occurred_at": row.created_at.isoformat(),
                "action_url": _action_url(row),
            }
            for row in created
        ]

    return {"activity": activity, "assignments": assignments, "collections": []}


register("scheduling", provide)
