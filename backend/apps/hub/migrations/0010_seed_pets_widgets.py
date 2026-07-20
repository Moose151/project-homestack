"""Seed the Pets Hub widgets (Node Spec 8).

Content is assembled by the Hub service via permission-filtered selectors (no cross-node model
imports, D4). Kiosk support is off for now (the highly-visual kiosk pet-care view is a later
slice); both widgets are enabled by default.

- pets_reminders    — treatments due (flea/worming/vaccination/medication/grooming).
- pets_appointments — upcoming vet appointments.
"""
from django.db import migrations

_WIDGETS = [
    {
        "key": "pets_reminders",
        "name": "Pet reminders",
        "description": "Pet treatments that are due or overdue.",
        "display_order": 12,
    },
    {
        "key": "pets_appointments",
        "name": "Vet appointments",
        "description": "Upcoming vet and grooming appointments.",
        "display_order": 13,
    },
]


def seed_forward(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HouseholdHubWidget = apps.get_model("hub", "HouseholdHubWidget")
    Household = apps.get_model("core", "Household")
    Node = apps.get_model("nodes", "Node")
    household = Household.objects.order_by("id").first()
    node = Node.objects.filter(key="pets").first()

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
        ("hub", "0009_seed_home_wiki_widgets"),
        ("core", "0002_seed_household"),
        ("nodes", "0002_seed_nodes"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
