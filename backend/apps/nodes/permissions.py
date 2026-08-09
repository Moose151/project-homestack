"""Permission helpers shared by node discovery, routes and contributed surfaces."""

from __future__ import annotations

from apps.permissions.resolver import resolve_permission


# Most catalogue keys match the central permission resource. Home Wiki predates
# that convention; callers should not need to know about the naming exception.
_PERMISSION_RESOURCE_BY_NODE = {
    "home_wiki": "homewiki",
}


def permission_resource_for_node(node_key: str) -> str:
    return _PERMISSION_RESOURCE_BY_NODE.get(node_key, node_key)


def can_view_node(user, node_key: str) -> bool:
    return resolve_permission(user, "view", permission_resource_for_node(node_key))
