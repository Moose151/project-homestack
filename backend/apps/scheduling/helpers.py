"""Scheduling helper — sync_event_for / delete_event_for (D7, D8).

Node services call ONLY these two functions to manage CalendarEvents for their records.
They must NEVER call CalendarEvent.objects.create/update/delete directly (D7).

Usage (in a node service, e.g. atlas/services.py)
-------------------------------------------------
    from apps.scheduling.helpers import delete_event_for, sync_event_for

    reminder = AtlasReminder(...)
    reminder.save()
    sync_event_for(reminder)        # creates CalendarEvent; writes calendar_event_id back

    reminder.title = "Updated"
    reminder.save()
    sync_event_for(reminder)        # updates the existing CalendarEvent

    reminder.soft_delete()
    delete_event_for(reminder)      # hard-deletes the CalendarEvent
"""
from __future__ import annotations


def sync_event_for(record) -> None:
    """Create or update the CalendarEvent that mirrors this node record.

    If ``record.get_calendar_data()`` returns None, or has no ``start_at``, any
    existing linked event is deleted instead.

    calendar_event_id is written back to the record via a targeted UPDATE so that
    service-layer save hooks are not re-triggered.
    """
    from apps.nodes.models import Node
    from apps.scheduling.models import CalendarEvent

    data = record.get_calendar_data()
    if not data or not data.get("start_at"):
        delete_event_for(record)
        return

    node_key = record.get_calendar_node_key()
    node = Node.objects.filter(key=node_key).first() if node_key else None

    event_fields = {
        "household": record.household,
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "start_at": data["start_at"],
        "end_at": data.get("end_at"),
        "is_all_day": data.get("is_all_day", False),
        "recurrence_rule": data.get("recurrence_rule", ""),
        "visibility": data.get("visibility", "household"),
        "sensitivity": data.get("sensitivity", "normal"),
        "colour": data.get("colour", ""),
        "source_node": node,
        "source_record_type": type(record).__name__,
        "source_record_id": record.pk,
        "updated_by": getattr(record, "updated_by", None),
    }
    if "assigned_to_person_id" in data:
        event_fields["assigned_to_person_id"] = data["assigned_to_person_id"]

    existing_id = getattr(record, "calendar_event_id", None)
    if existing_id:
        try:
            event = CalendarEvent.all_objects.get(pk=existing_id)
            for key, val in event_fields.items():
                if key != "household":
                    setattr(event, key, val)
            event.save()
            return
        except CalendarEvent.DoesNotExist:
            pass  # create a fresh event below

    event_fields["created_by"] = getattr(record, "created_by", None)
    event = CalendarEvent.objects.create(**event_fields)

    # Write calendar_event_id back without triggering service-layer save hooks.
    type(record).objects.filter(pk=record.pk).update(calendar_event_id=event.pk)
    record.calendar_event_id = event.pk


def delete_event_for(record) -> None:
    """Hard-delete the CalendarEvent linked to this record (if any) and clear the FK."""
    from apps.scheduling.models import CalendarEvent

    existing_id = getattr(record, "calendar_event_id", None)
    if not existing_id:
        return

    CalendarEvent.all_objects.filter(pk=existing_id).delete()

    type(record).objects.filter(pk=record.pk).update(calendar_event_id=None)
    record.calendar_event_id = None
