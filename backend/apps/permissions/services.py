"""
permissions services — write operations for per-user permission overrides.

Only admins should call these; enforcement is the caller's responsibility until
the admin endpoints are built in a later phase.
"""
from __future__ import annotations

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.permissions.models import Permission, UserPermission


def grant_user_permission(target_user: User, codename: str) -> UserPermission:
    """Grant target_user an explicit permission override (is_granted=True)."""
    perm = Permission.objects.get(code=codename)
    override, _ = UserPermission.objects.update_or_create(
        user=target_user,
        permission=perm,
        defaults={"is_granted": True, "household": get_active_household()},
    )
    return override


def deny_user_permission(target_user: User, codename: str) -> UserPermission:
    """Explicitly deny target_user a permission (is_granted=False — blocks role grant)."""
    perm = Permission.objects.get(code=codename)
    override, _ = UserPermission.objects.update_or_create(
        user=target_user,
        permission=perm,
        defaults={"is_granted": False, "household": get_active_household()},
    )
    return override


def clear_user_permission(target_user: User, codename: str) -> None:
    """Remove the per-user override, reverting to role default."""
    perm = Permission.objects.get(code=codename)
    UserPermission.objects.filter(user=target_user, permission=perm).delete()
