"""Meridian household settings — typed wrapper over the shared NodeSetting store (Phase 2.17).

No new table (D-consistent): settings live as `NodeSetting` rows under the `meridian` node.
Defaults mirror the legacy app's HouseholdSettings.
"""
from __future__ import annotations

from apps.nodes.selectors import list_node_settings
from apps.nodes.services import update_node_settings

NODE_KEY = "meridian"

DEFAULTS: dict = {
    "points_label": "points",
    "group_goals_enabled": True,
    "wishlist_requests_enabled": True,
    "auto_end_streaks": False,
}


def get_settings() -> dict:
    """Return the full settings dict, defaults overlaid with any stored values."""
    stored = {s.key: s.value_json for s in list_node_settings(NODE_KEY)}
    return {key: stored.get(key, default) for key, default in DEFAULTS.items()}


def get_setting(key: str):
    return get_settings().get(key, DEFAULTS.get(key))


def update_settings(acting_user, data: dict) -> dict:
    """Persist only known setting keys, then return the merged settings."""
    clean = {k: v for k, v in data.items() if k in DEFAULTS}
    if clean:
        update_node_settings(acting_user, NODE_KEY, clean)
    return get_settings()
