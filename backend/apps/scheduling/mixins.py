"""CalendarSyncMixin — contract for models that maintain a CalendarEvent shadow (D7).

Any HouseholdBaseModel subclass that wants calendar entries inherits this mixin and
implements the two required methods. Services then call sync_event_for / delete_event_for
from scheduling.helpers instead of writing CalendarEvent rows directly (D7).
"""
from __future__ import annotations


class CalendarSyncMixin:
    """Mixin for records that own a CalendarEvent.

    Contract for implementing models
    ---------------------------------
    1. Add a nullable IntegerField named ``calendar_event_id``.
    2. Implement ``get_calendar_data()`` — return a dict with calendar fields, or None
       to signal that no event should exist (e.g. a reminder with no due_at).
    3. Implement ``get_calendar_node_key()`` — return the Node.key string (e.g. 'atlas').
    4. Call ``sync_event_for(self)`` from the service after each save.
    5. Call ``delete_event_for(self)`` from the service on soft-delete.

    get_calendar_data() dict keys
    ------------------------------
    Required:  title (str), start_at (datetime)
    Optional:  end_at, is_all_day, description, recurrence_rule,
               visibility, sensitivity, colour, assigned_to_person_id
    """

    def get_calendar_data(self) -> dict | None:
        raise NotImplementedError(
            f"{type(self).__name__} must implement get_calendar_data()"
        )

    def get_calendar_node_key(self) -> str:
        raise NotImplementedError(
            f"{type(self).__name__} must implement get_calendar_node_key()"
        )
