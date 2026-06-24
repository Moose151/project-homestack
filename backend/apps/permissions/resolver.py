"""
Central permission resolver (D10, Architecture §7).

ONE function — resolve_permission(user, action, resource) → bool — combines:
  1. Authentication / active check
  2. Child-account safety block (writes always denied)
  3. Per-user explicit override (UserPermission.is_granted)
  4. Role-default grant (RolePermission lookup)

No view may check permissions ad hoc; all enforcement goes through here.

Future extensions hook into this function:
  - node-enabled check (Phase 1.6: household_nodes.is_enabled)
  - record-level visibility / sensitivity (Phase 1.8+)
  - re-auth state for sensitive nodes (Phase 1.8+)
"""
from __future__ import annotations


def resolve_permission(user, action: str, resource: str) -> bool:
    """Return True iff the user is allowed to perform action on resource.

    user     — request.user (may be AnonymousUser or None)
    action   — 'view' | 'create' | 'edit' | 'delete'
    resource — resource/node key, e.g. 'people', 'atlas'
    """
    # Deferred import avoids circular references at module load time.
    from apps.permissions.models import RolePermission, UserPermission

    # --- Basic auth gate ---
    if user is None:
        return False
    if not getattr(user, "is_authenticated", False):
        return False
    if not getattr(user, "is_active", False):
        return False

    # --- Child-account safety: children may never write anything ---
    if getattr(user, "is_child_account", False) and action != "view":
        return False

    codename = f"{resource}.{action}"

    # --- 1. Explicit per-user override takes precedence over role default ---
    try:
        override = UserPermission.objects.get(user=user, permission__code=codename)
        return override.is_granted
    except UserPermission.DoesNotExist:
        pass

    # --- 2. Role-based default: presence of RolePermission row = grant ---
    return RolePermission.objects.filter(
        role__name=user.role,
        permission__code=codename,
    ).exists()
