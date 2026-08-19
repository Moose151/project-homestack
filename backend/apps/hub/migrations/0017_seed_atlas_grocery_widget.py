"""Seed the atlas_grocery Dashboard widget (D19 §K/§L).

Grocery items were previously indistinguishable from To-dos on the Hub because the
`atlas_todos` widget pulled from every AtlasList regardless of list_type. Now that the
selector is scoped to `list_type='todo'` (see apps.atlas.selectors.list_open_items), Grocery
needs its own widget so it doesn't just disappear from the Dashboard.
"""
from django.db import migrations


def seed_forward(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HouseholdHubWidget = apps.get_model("hub", "HouseholdHubWidget")
    Household = apps.get_model("core", "Household")
    Node = apps.get_model("nodes", "Node")

    node = Node.objects.filter(key="atlas").first()
    widget, _ = HubWidget.objects.get_or_create(
        key="atlas_grocery",
        defaults={
            "name": "Grocery",
            "description": "Remaining items on the household grocery list.",
            "source_node": node,
            "supports_kiosk": True,
            "display_order": 1,
        },
    )
    for household in Household.objects.all():
        HouseholdHubWidget.objects.get_or_create(
            household=household,
            widget=widget,
            defaults={"is_enabled": True, "display_order": 1},
        )


def seed_reverse(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HubWidget.objects.filter(key="atlas_grocery").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("hub", "0016_due_before_payday_widget"),
        ("nodes", "0002_seed_nodes"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
