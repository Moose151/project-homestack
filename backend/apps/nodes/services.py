"""nodes services — enable/disable and settings mutations."""
from __future__ import annotations

from apps.core.models import get_active_household
from apps.nodes.models import HouseholdNode, Node, NodeSetting


def _get_or_404(node_key: str) -> tuple[Node, HouseholdNode]:
    """Return (Node, HouseholdNode) or raise Node.DoesNotExist."""
    household = get_active_household()
    node = Node.objects.get(key=node_key)
    hn, _ = HouseholdNode.objects.get_or_create(
        household=household, node=node, defaults={"is_enabled": False}
    )
    return node, hn


def enable_node(acting_user, node_key: str) -> HouseholdNode:
    from apps.audit.helpers import log_audit
    node, hn = _get_or_404(node_key)
    if not hn.is_enabled:
        hn.is_enabled = True
        hn.save(update_fields=["is_enabled", "updated_at"])
    log_audit("node_enabled", user=acting_user, target_node=node)
    return hn


def disable_node(acting_user, node_key: str) -> HouseholdNode:
    from apps.audit.helpers import log_audit
    node, hn = _get_or_404(node_key)
    if hn.is_enabled:
        hn.is_enabled = False
        hn.save(update_fields=["is_enabled", "updated_at"])
    log_audit("node_disabled", user=acting_user, target_node=node)
    return hn


def update_node_settings(acting_user, node_key: str, settings: dict) -> list[NodeSetting]:
    """Upsert NodeSetting rows for each key in settings dict."""
    from apps.audit.helpers import log_audit
    household = get_active_household()
    node = Node.objects.get(key=node_key)
    updated = []
    for key, value in settings.items():
        obj, _ = NodeSetting.objects.update_or_create(
            household=household,
            node=node,
            key=key,
            defaults={"value_json": value},
        )
        updated.append(obj)
    log_audit("node_settings_updated", user=acting_user, target_node=node,
              metadata={"keys": list(settings.keys())})
    return updated
