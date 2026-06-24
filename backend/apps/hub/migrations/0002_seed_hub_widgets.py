"""Seed default hub widgets and enable them for the household.

atlas_todos     — open to-do items across all lists
atlas_reminders — upcoming reminders (next 7 days)

Both support kiosk mode.
"""
from django.db import migrations

_WIDGETS = [
    {
        "key": "atlas_todos",
        "name": "To-Do Items",
        "description": "Open items across all your lists.",
        "node_key": "atlas",
        "supports_kiosk": True,
        "display_order": 1,
    },
    {
        "key": "atlas_reminders",
        "name": "Reminders",
        "description": "Upcoming reminders due in the next 7 days.",
        "node_key": "atlas",
        "supports_kiosk": True,
        "display_order": 2,
    },
]


def seed_forward(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HouseholdHubWidget = apps.get_model("hub", "HouseholdHubWidget")
    Household = apps.get_model("core", "Household")
    Node = apps.get_model("nodes", "Node")

    household = Household.objects.order_by("id").first()
    if not household:
        return

    for w in _WIDGETS:
        node = Node.objects.filter(key=w["node_key"]).first()
        widget, _ = HubWidget.objects.get_or_create(
            key=w["key"],
            defaults={
                "name": w["name"],
                "description": w["description"],
                "source_node": node,
                "supports_kiosk": w["supports_kiosk"],
                "display_order": w["display_order"],
            },
        )
        HouseholdHubWidget.objects.get_or_create(
            household=household,
            widget=widget,
            defaults={"is_enabled": True, "display_order": w["display_order"]},
        )


def seed_reverse(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HubWidget.objects.filter(key__in=[w["key"] for w in _WIDGETS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("hub", "0001_initial"),
        ("nodes", "0002_seed_nodes"),
        ("core", "0002_seed_household"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
