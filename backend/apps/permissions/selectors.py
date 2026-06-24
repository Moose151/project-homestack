"""
permissions selectors — read-only queries for permission data.
"""
from __future__ import annotations

from apps.accounts.models import User
from apps.permissions.models import Permission, Role, RolePermission, UserPermission


def list_permissions_for_user(user: User) -> list[str]:
    """Return all permission codenames effectively granted to user (role + overrides)."""
    # Role defaults
    role_codes = set(
        RolePermission.objects.filter(role__name=user.role).values_list(
            "permission__code", flat=True
        )
    )
    # Per-user overrides
    overrides = UserPermission.objects.filter(user=user).select_related("permission")
    for override in overrides:
        if override.is_granted:
            role_codes.add(override.permission.code)
        else:
            role_codes.discard(override.permission.code)
    return sorted(role_codes)


def get_role_by_name(name: str) -> Role | None:
    try:
        return Role.objects.get(name=name)
    except Role.DoesNotExist:
        return None
