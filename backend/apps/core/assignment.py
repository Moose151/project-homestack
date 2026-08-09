"""Shared write helpers for multi-person assignment.

An assignment used to be a single `assigned_to_person` FK where null meant "the whole
household". That could not express "both of us", so every assignable record now carries an
`assigned_to_people` M2M: empty means the whole household, one or more people means each of
them (owner request, 2026-08-09).

A many-to-many cannot be set through the model constructor or `setattr`, so services pop the
ids out of the payload, save the row, then apply them. Records that mirror to the Calendar
(D7) must apply assignees *before* calling the scheduling helper, because
`get_calendar_data()` reads the relation.
"""
from __future__ import annotations

# The serializer maps `assigned_to_person_ids` onto the model relation, so this is the
# key that reaches a service in validated_data.
ASSIGNEE_FIELD = "assigned_to_people"


def pop_assignees(data: dict) -> list[int] | None:
    """Remove assignee ids from a service payload.

    Returns None when the caller did not mention assignment at all — a partial update must
    leave the existing assignees alone rather than clearing them.
    """
    if ASSIGNEE_FIELD not in data:
        return None
    return list(data.pop(ASSIGNEE_FIELD) or [])


def apply_assignees(obj, person_ids: list[int] | None) -> None:
    """Set the record's assignees, or leave them untouched when None was passed."""
    if person_ids is not None:
        obj.assigned_to_people.set(person_ids)
