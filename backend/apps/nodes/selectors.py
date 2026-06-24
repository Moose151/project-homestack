"""nodes selectors — read-only queries."""
from __future__ import annotations

from apps.core.models import get_active_household
from apps.nodes.models import HouseholdNode, Node, NodeSetting


def list_household_nodes() -> list[HouseholdNode]:
    household = get_active_household()
    return list(
        HouseholdNode.objects.filter(household=household)
        .select_related("node")
        .order_by("display_order", "node__key")
    )


def get_household_node(node_key: str) -> HouseholdNode | None:
    household = get_active_household()
    try:
        return HouseholdNode.objects.select_related("node").get(
            household=household, node__key=node_key
        )
    except HouseholdNode.DoesNotExist:
        return None


def get_node_by_key(node_key: str) -> Node | None:
    try:
        return Node.objects.get(key=node_key)
    except Node.DoesNotExist:
        return None


def list_node_settings(node_key: str) -> list[NodeSetting]:
    household = get_active_household()
    return list(NodeSetting.objects.filter(household=household, node__key=node_key))
