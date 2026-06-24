"""
accounts selectors — read-only queries for User records.

All reads go through the default HouseholdManager (excludes soft-deleted).
Heavy filtering or search will route through the visibility mixin once Phase 1.5 lands.
"""
from __future__ import annotations

from apps.accounts.models import User


def get_user_by_id(user_id: int) -> User | None:
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return None


def get_user_by_username(username: str) -> User | None:
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None


def list_active_users() -> list[User]:
    return list(User.objects.filter(is_active=True).order_by("display_name"))
