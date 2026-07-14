"""hub selectors — read the widget catalogue and per-household / per-user configuration.

Used by the config endpoints (M2.5 Workstream A). The assembled *content* of each widget
for the dashboard lives in `hub.services.get_hub_widgets`; this module is configuration only.
"""
from __future__ import annotations

from apps.hub.models import HouseholdHubWidget, HubWidget, UserHubWidget


def list_widget_config(user) -> list[dict]:
    """Return every catalogue widget with its household + per-user configuration.

    Household state (enabled/order/size) is the shared default; per-user state overrides
    visibility and order for this user only. Drives the Hub configuration UI.
    """
    household_state = {
        hw.widget_id: hw
        for hw in HouseholdHubWidget.objects.filter(household=user.household).select_related("widget")
    }
    user_state = {uw.widget_id: uw for uw in UserHubWidget.objects.filter(user=user)}

    # Widgets from disabled stacks aren't offered in the Customise list either.
    from apps.nodes.models import HouseholdNode
    enabled_node_ids = set(
        HouseholdNode.objects.filter(household=user.household, is_enabled=True)
        .values_list("node_id", flat=True)
    )

    rows = []
    for widget in HubWidget.objects.select_related("source_node").all():
        if widget.source_node_id and widget.source_node_id not in enabled_node_ids:
            continue
        hh = household_state.get(widget.id)
        uu = user_state.get(widget.id)
        rows.append({
            "key": widget.key,
            "name": widget.name,
            "description": widget.description,
            "source_node": widget.source_node.key if widget.source_node else None,
            "supports_kiosk": widget.supports_kiosk,
            "household_enabled": hh.is_enabled if hh else False,
            "household_order": hh.display_order if hh else widget.display_order,
            "size": hh.size if hh else "medium",
            "user_hidden": (uu is not None and not uu.is_enabled),
            "user_order": uu.display_order if uu else None,
        })

    rows.sort(key=lambda r: (
        r["user_order"] if r["user_order"] is not None else r["household_order"],
        r["key"],
    ))
    return rows
