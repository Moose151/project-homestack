"""core selectors."""
from apps.core.models import Household, get_active_household


def get_household() -> Household | None:
    return get_active_household()
