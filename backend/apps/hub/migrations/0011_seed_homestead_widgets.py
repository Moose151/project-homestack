"""Seed the Homestead Hub widgets (Node Spec 25).

Content is assembled by the Hub service via permission-filtered selectors (no cross-node model
imports, D4). Kiosk off for now. All enabled by default.

- homestead_maintenance — upkeep/renewals that are due or overdue.
- homestead_warranties   — appliance warranties expiring soon.
- homestead_improvements — active home improvements.
"""
from django.db import migrations

_WIDGETS = [
    {
        "key": "homestead_maintenance",
        "name": "Home maintenance",
        "description": "Home upkeep and renewals that are due or overdue.",
        "display_order": 14,
    },
    {
        "key": "homestead_warranties",
        "name": "Warranties expiring",
        "description": "Appliance warranties coming up for expiry.",
        "display_order": 15,
    },
    {
        "key": "homestead_improvements",
        "name": "Home improvements",
        "description": "Active home improvement projects.",
        "display_order": 16,
    },
]


def seed_forward(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HouseholdHubWidget = apps.get_model("hub", "HouseholdHubWidget")
    Household = apps.get_model("core", "Household")
    Node = apps.get_model("nodes", "Node")
    household = Household.objects.order_by("id").first()
    node = Node.objects.filter(key="homestead").first()

    for w in _WIDGETS:
        widget, _ = HubWidget.objects.get_or_create(
            key=w["key"],
            defaults={
                "name": w["name"],
                "description": w["description"],
                "source_node": node,
                "supports_kiosk": False,
                "display_order": w["display_order"],
            },
        )
        if household:
            HouseholdHubWidget.objects.get_or_create(
                household=household, widget=widget,
                defaults={"is_enabled": True, "display_order": w["display_order"], "size": "medium"},
            )


def seed_reverse(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HubWidget.objects.filter(key__in=[w["key"] for w in _WIDGETS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("hub", "0010_seed_pets_widgets"),
        ("core", "0002_seed_household"),
        ("nodes", "0005_seed_homestead_node"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
