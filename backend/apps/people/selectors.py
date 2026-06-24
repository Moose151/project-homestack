"""
people selectors — read-only queries for Person records.

All reads go through HouseholdManager (excludes soft-deleted) and then through
apply_visibility so list endpoints only return rows the user may see (D10).
"""
from __future__ import annotations

from apps.people.models import Person
from apps.permissions.visibility import apply_visibility


def list_people(user=None) -> list[Person]:
    qs = Person.objects.order_by("display_name")
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_person_by_id(person_id: int) -> Person | None:
    try:
        return Person.objects.get(pk=person_id)
    except Person.DoesNotExist:
        return None
