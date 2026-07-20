"""Add the Homestead node to the node catalogue (Node Spec 25).

Homestead is the household's home/property hub. Per the owner decision (2026-07-21) it folds the
*home* scope of the planned Assets node (home maintenance, appliances, warranties, documents) into
one warm surface, plus house dates and a lightweight improvements list. Disabled by default —
enable it in Settings.
"""
from django.db import migrations


def seed_forward(apps, schema_editor):
    Household = apps.get_model("core", "Household")
    Node = apps.get_model("nodes", "Node")
    HouseholdNode = apps.get_model("nodes", "HouseholdNode")

    node, _ = Node.objects.get_or_create(
        key="homestead",
        defaults={
            "name": "Homestead",
            "description": "Home upkeep, appliances & warranties, service contacts and improvements.",
            "icon": "home",
            "is_core": False,
            "is_enabled_by_default": False,
            "supports_kiosk": False,
            "supports_sensitive_lock": False,
        },
    )
    household = Household.objects.order_by("id").first()
    if household:
        HouseholdNode.objects.get_or_create(
            household=household,
            node=node,
            defaults={"is_enabled": False, "display_order": 13},
        )


def seed_reverse(apps, schema_editor):
    Node = apps.get_model("nodes", "Node")
    Node.objects.filter(key="homestead").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("nodes", "0004_seed_books_node"),
        ("core", "0002_seed_household"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
