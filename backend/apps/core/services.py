"""core services — household mutations."""
from __future__ import annotations

from typing import Any

from apps.core.models import Household, get_active_household


def update_household(acting_user, **data: Any) -> Household:
    household = get_active_household()
    # Kept as an explicit allow-list rather than writing whatever the serializer validated: it
    # is the last gate before a household-wide row is mutated, and `slug` in particular must
    # never be settable this way.
    #
    # The location fields belong here too. They were added for Calendar Sources and accepted by
    # HouseholdWriteSerializer, but omitting them here meant a PATCH validated, returned 200,
    # and silently discarded them — so Settings appeared to save and reverted to "Not set" on
    # the next load. A field the write serializer accepts must be represented here.
    allowed = {
        "name", "timezone", "default_locale", "family_colour",
        "country", "region", "locality", "postcode",
        "calendar_default_view", "calendar_week_start", "calendar_time_format",
    }
    for field, value in data.items():
        if field in allowed:
            setattr(household, field, value)
    household.save()
    return household
