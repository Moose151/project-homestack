"""
Central permission resolver (D10, Architecture §7).

ONE function — resolve_permission(user, action, resource, record=...) → bool — combines:
  1. Authentication / active check
  2. Child-account safety block (writes always denied)
  3. Per-user explicit override (UserPermission.is_granted)
  4. Role-default grant (RolePermission lookup)
  5. Optional record visibility / sensitivity and current re-auth state

No view may check permissions ad hoc; all enforcement goes through here.

Future extension: node-enabled state can be folded into this function when all node views
declare their node key consistently.
"""
from __future__ import annotations

# Narrow per-resource carve-out to the child-account write block (Milestone 2).
# Children may never create/edit/delete content, but a node may declare a small set
# of safe actions they ARE allowed to perform (still subject to the normal role grant
# below). Meridian needs this so kids can complete tasks and request rewards on the
# kiosk — the node's whole purpose — without weakening the global child-safety block.
_CHILD_SAFE_ACTIONS: dict[str, frozenset[str]] = {
    "meridian": frozenset({"complete", "request", "contribute"}),
}


def resolve_permission(
    user,
    action: str,
    resource: str,
    *,
    record=None,
    sensitive_unlocked: bool = False,
    kiosk: bool = False,
) -> bool:
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

    # --- Child-account safety: children may never write anything, except a small
    #     allowlist of node-declared safe actions (still requires the role grant below). ---
    if getattr(user, "is_child_account", False) and action != "view":
        if action not in _CHILD_SAFE_ACTIONS.get(resource, frozenset()):
            return False

    codename = f"{resource}.{action}"

    # --- 1. Explicit per-user override takes precedence over role default ---
    try:
        override = UserPermission.objects.get(user=user, permission__code=codename)
        allowed = override.is_granted
    except UserPermission.DoesNotExist:
        allowed = RolePermission.objects.filter(
            role__name=user.role,
            permission__code=codename,
        ).exists()

    if not allowed or record is None:
        return allowed

    # --- 3. Optional record policy: central visibility/sensitivity enforcement. ---
    visibility = getattr(record, "visibility", None)
    sensitivity = getattr(record, "sensitivity", "normal")
    role = getattr(user, "role", "guest")
    is_child = getattr(user, "is_child_account", False)
    if visibility is not None:
        if role in ("admin", "manager") and not is_child:
            pass
        elif role == "user" and not is_child:
            if visibility == "private" and getattr(record, "created_by_id", None) != user.id:
                return False
            if visibility not in ("household", "private"):
                return False
        elif visibility != "household":
            return False

    is_sensitive = visibility == "sensitive" or sensitivity != "normal"
    if is_sensitive and (is_child or kiosk or not sensitive_unlocked):
        return False

    # Members can remove their own uploads; adults with broader role grants can manage all.
    if resource == "attachments" and action == "delete" and role not in ("admin", "manager"):
        return getattr(record, "created_by_id", None) == user.id
    return True
