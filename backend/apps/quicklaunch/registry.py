"""The registry of destinations a Quick Launch shortcut is allowed to point at.

Two properties matter more than anything else here.

**A shortcut stores intent, not a route.** Nothing a user sends becomes a URL. They choose a
registered ``key``, and this module decides what that means *right now* — so internal routes can
be changed later without breaking saved shortcuts, and there is no field anywhere in which an
arbitrary internal path or external URL could be smuggled.

**A shortcut grants nothing.** Every entry carries its own availability check, evaluated at
launch time against the current user, and every object-backed entry re-resolves its record
through the node's own selectors so household scoping and visibility are the node's rules, not a
copy of them. A shortcut saved when someone had access resolves to "unavailable" the moment they
stop having it.

Nodes advertise their destinations here rather than Quick Launch knowing each node's internals,
and the client is handed labels and eligibility from this one place instead of growing a switch
statement per page.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from apps.nodes.permissions import can_view_node

# --- outcomes -------------------------------------------------------------------------------

@dataclass(frozen=True)
class Resolution:
    """What a launch attempt produced."""

    status: str            # "ok" | "unavailable" | "locked"
    route: str = ""        # only when status == "ok"
    label: str = ""
    reason: str = ""       # user-facing, safe to show; never leaks record detail
    node_key: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "ok"


OK = "ok"
UNAVAILABLE = "unavailable"
LOCKED = "locked"


@dataclass(frozen=True)
class Target:
    key: str
    label: str
    description: str
    icon: str
    # Owning node key, or "" for an always-on core surface. Drives the enabled-node check and
    # the user-facing product name shown in the picker.
    node_key: str
    # "open" today; "action" entries open a bounded form, never perform the action themselves.
    target_type: str
    # Builds the destination for a shortcut. (user, obj) -> route string.
    route: Callable
    requires_object: bool = False
    # Lists the selectable records for an object-backed target: (user) -> [(id, label), ...].
    list_objects: Callable | None = None
    # Fetches one record for this user, or None: (user, object_id) -> obj | None.
    get_object: Callable | None = None
    # True when the owning node is behind the sensitive re-auth gate.
    sensitive: bool = False
    launch_modes: tuple = ("normal", "focused")
    # Extra availability beyond node-enabled + node-permission, e.g. a settings flag.
    extra_available: Callable | None = None


REGISTRY: dict[str, Target] = {}


def register(target: Target) -> Target:
    REGISTRY[target.key] = target
    return target


# --- shared helpers -------------------------------------------------------------------------

def _node_enabled(node_key: str) -> bool:
    if not node_key:
        return True  # core surface (Dashboard, Calendar) — always present
    from apps.nodes.selectors import get_household_node
    config = get_household_node(node_key)
    return bool(config and config.is_enabled and not config.is_hidden)


def is_available(target: Target, user) -> bool:
    """Whether this user could use this target at all, ignoring any specific record."""
    if not _node_enabled(target.node_key):
        return False
    if target.node_key and not can_view_node(user, target.node_key):
        return False
    if target.extra_available and not target.extra_available(user):
        return False
    return True


def _sensitive_locked(target: Target, request) -> bool:
    """Whether the sensitive gate currently stands between this user and the target.

    Deliberately the same question the node's own views ask, via apps.nodes.access — a shortcut
    must behave exactly like ordinary navigation, including the unlock prompt.
    """
    if not target.sensitive or request is None:
        return False
    from apps.accounts.services import is_reauthed
    from apps.nodes.access import node_requires_reauth
    return node_requires_reauth(target.node_key) and not is_reauthed(request)


def resolve(shortcut, user, request=None) -> Resolution:
    """Resolve one saved shortcut to a destination for this user, right now."""
    target = REGISTRY.get(shortcut.target_key)
    if target is None:
        # A target removed in a later release. Say so plainly rather than guessing a fallback.
        return Resolution(UNAVAILABLE, reason="This shortcut is no longer available.")

    if not is_available(target, user):
        return Resolution(
            UNAVAILABLE,
            reason="This shortcut is no longer available.",
            node_key=target.node_key,
        )

    obj = None
    if target.requires_object:
        if shortcut.target_object_id is None or target.get_object is None:
            return Resolution(UNAVAILABLE, reason="This shortcut is no longer available.")
        obj = target.get_object(user, shortcut.target_object_id)
        if obj is None:
            # Deleted, or never visible to this user. Both answer the same way on purpose: the
            # difference would itself disclose that a record exists.
            return Resolution(
                UNAVAILABLE,
                reason="This shortcut is no longer available.",
                node_key=target.node_key,
            )

    if _sensitive_locked(target, request):
        return Resolution(
            LOCKED,
            route=target.route(user, obj),
            label=label_for(shortcut, target, obj),
            reason="Unlock to open this.",
            node_key=target.node_key,
        )

    return Resolution(
        OK,
        route=target.route(user, obj),
        label=label_for(shortcut, target, obj),
        node_key=target.node_key,
    )


def label_for(shortcut, target: Target, obj=None) -> str:
    if shortcut.custom_label:
        return shortcut.custom_label
    if obj is not None:
        return getattr(obj, "title", None) or getattr(obj, "name", None) or target.label
    return target.label


def catalogue(user) -> list[dict]:
    """Targets this user may actually choose, with their selectable records.

    Returning only available targets is what stops the picker advertising a node the household
    has disabled or this person cannot open.
    """
    out: list[dict] = []
    for target in REGISTRY.values():
        if not is_available(target, user):
            continue
        objects: list[dict] = []
        if target.requires_object and target.list_objects:
            objects = [
                {"id": obj_id, "label": obj_label}
                for obj_id, obj_label in target.list_objects(user)
            ]
            if not objects:
                # Nothing to point at yet — offering it would only produce a dead shortcut.
                continue
        out.append({
            "key": target.key,
            "label": target.label,
            "description": target.description,
            "icon": target.icon,
            "node_key": target.node_key,
            "target_type": target.target_type,
            "requires_object": target.requires_object,
            "sensitive": target.sensitive,
            "launch_modes": list(target.launch_modes),
            "objects": objects,
        })
    return out


def validate_selection(target_key: str, target_object_id, user):
    """Check a proposed shortcut before it is stored. Returns the resolved Target."""
    from rest_framework import serializers

    target = REGISTRY.get(target_key)
    if target is None:
        raise serializers.ValidationError({"target_key": "Unknown shortcut destination."})
    if not is_available(target, user):
        raise serializers.ValidationError({"target_key": "That destination is not available to you."})
    if target.requires_object:
        if target_object_id is None:
            raise serializers.ValidationError({"target_object_id": "Choose what to open."})
        if target.get_object is None or target.get_object(user, target_object_id) is None:
            raise serializers.ValidationError({"target_object_id": "That item is not available."})
    elif target_object_id is not None:
        raise serializers.ValidationError({"target_object_id": "This destination takes no item."})
    return target
