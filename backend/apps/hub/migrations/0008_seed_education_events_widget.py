"""Seed the Education "school events" Hub widget (Node Spec 8).

Completes the Education Hub widget set with `education_events` — upcoming excursions, school
events, term dates and milestones. Content is assembled by the Hub service via a
permission-filtered selector (no cross-node model imports, D4). Kiosk support is off for now
(uni-first slice is adult/web-facing).
"""
from django.db import migrations

_WIDGET = {
    "key": "education_events",
    "name": "School events",
    "description": "Upcoming excursions, school events, term dates and milestones.",
    "display_order": 8,
}


def seed_forward(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HouseholdHubWidget = apps.get_model("hub", "HouseholdHubWidget")
    Household = apps.get_model("core", "Household")
    Node = apps.get_model("nodes", "Node")
    household = Household.objects.order_by("id").first()
    node = Node.objects.filter(key="education").first()

    widget, _ = HubWidget.objects.get_or_create(
        key=_WIDGET["key"],
        defaults={
            "name": _WIDGET["name"],
            "description": _WIDGET["description"],
            "source_node": node,
            "supports_kiosk": False,
            "display_order": _WIDGET["display_order"],
        },
    )
    if household:
        HouseholdHubWidget.objects.get_or_create(
            household=household, widget=widget,
            defaults={"is_enabled": True, "display_order": _WIDGET["display_order"], "size": "medium"},
        )


def seed_reverse(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HubWidget.objects.filter(key=_WIDGET["key"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("hub", "0007_seed_hub_v2_widgets"),
        ("core", "0002_seed_household"),
        ("nodes", "0002_seed_nodes"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
