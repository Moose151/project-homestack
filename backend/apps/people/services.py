"""
people services — write operations for Person records (D12).

All mutations live here so views stay thin. created_by / updated_by are always set to
the acting User (D12); the Person being created/modified is the subject, not the actor.
"""
from __future__ import annotations

from typing import Any

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.people.models import Person


def create_person(acting_user: User, **data: Any) -> Person:
    """Create a Person in the active household, stamped with the acting user."""
    household = get_active_household()
    person = Person(
        household=household,
        created_by=acting_user,
        updated_by=acting_user,
        **data,
    )
    person.save()
    return person


def update_person(acting_user: User, person: Person, **data: Any) -> Person:
    """Update allowed fields on a Person, re-stamping updated_by."""
    allowed = {
        "linked_user",
        "display_name",
        "preferred_name",
        "avatar",
        "colour",
        "date_of_birth",
        "profile_type",
        "notes",
    }
    for field, value in data.items():
        if field in allowed:
            setattr(person, field, value)
    person.updated_by = acting_user
    person.save()
    return person


def delete_person(acting_user: User, person: Person) -> None:
    """Soft-delete a Person (D12 — preserves audit trail and FK integrity)."""
    person.updated_by = acting_user
    person.save(update_fields=["updated_by", "updated_at"])
    person.soft_delete()
