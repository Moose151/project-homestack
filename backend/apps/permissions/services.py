"""
permissions services — write operations for per-user permission overrides.

Only admins should call these; enforcement is the caller's responsibility until
the admin endpoints are built in a later phase.

Every override is audited. Who may open the household's finances is exactly the kind of change
that needs to be answerable months later, and `acting_user` is optional only so internal
callers that have no request context still work — pass it wherever a person made the decision.
"""
from __future__ import annotations

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.permissions.models import Permission, UserPermission


def _log(action: str, acting_user: User | None, target_user: User, codename: str) -> None:
    from apps.audit.helpers import log_audit

    log_audit(
        action,
        user=acting_user,
        target_record_type="User",
        target_record_id=target_user.id,
        metadata={"permission": codename, "target_user": target_user.username},
    )


def grant_user_permission(
    target_user: User, codename: str, *, acting_user: User | None = None
) -> UserPermission:
    """Grant target_user an explicit permission override (is_granted=True)."""
    perm = Permission.objects.get(code=codename)
    override, _ = UserPermission.objects.update_or_create(
        user=target_user,
        permission=perm,
        defaults={"is_granted": True, "household": get_active_household()},
    )
    _log("permission_granted", acting_user, target_user, codename)
    return override


def deny_user_permission(
    target_user: User, codename: str, *, acting_user: User | None = None
) -> UserPermission:
    """Explicitly deny target_user a permission (is_granted=False — blocks role grant)."""
    perm = Permission.objects.get(code=codename)
    override, _ = UserPermission.objects.update_or_create(
        user=target_user,
        permission=perm,
        defaults={"is_granted": False, "household": get_active_household()},
    )
    _log("permission_denied", acting_user, target_user, codename)
    return override


def clear_user_permission(
    target_user: User, codename: str, *, acting_user: User | None = None
) -> None:
    """Remove the per-user override, reverting to role default."""
    perm = Permission.objects.get(code=codename)
    deleted, _ = UserPermission.objects.filter(user=target_user, permission=perm).delete()
    if deleted:
        _log("permission_cleared", acting_user, target_user, codename)
