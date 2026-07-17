"""Add the Books node to the node catalogue."""
from django.db import migrations


def seed_forward(apps, schema_editor):
    Household = apps.get_model("core", "Household")
    Node = apps.get_model("nodes", "Node")
    HouseholdNode = apps.get_model("nodes", "HouseholdNode")

    node, _ = Node.objects.get_or_create(
        key="books",
        defaults={
            "name": "Books",
            "description": "Personal reading shelves and shared book clubs.",
            "icon": "book-open",
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
            defaults={"is_enabled": False, "display_order": 12},
        )


def seed_reverse(apps, schema_editor):
    Node = apps.get_model("nodes", "Node")
    Node.objects.filter(key="books").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("nodes", "0003_enable_built_nodes"),
        ("core", "0002_seed_household"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
