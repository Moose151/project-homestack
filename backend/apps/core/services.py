"""core services — household mutations."""
from __future__ import annotations

from typing import Any

from apps.core.models import Household, get_active_household


def update_household(acting_user, **data: Any) -> Household:
    household = get_active_household()
    allowed = {
        "name", "timezone", "default_locale", "family_colour",
        "calendar_default_view", "calendar_week_start", "calendar_time_format",
    }
    for field, value in data.items():
        if field in allowed:
            setattr(household, field, value)
    household.save()
    return household
