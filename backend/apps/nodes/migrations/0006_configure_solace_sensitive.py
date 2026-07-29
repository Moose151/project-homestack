"""Ensure Solace is configured as a sensitive disabled stack."""
from django.db import migrations


def seed_forward(apps, schema_editor):
    Household = apps.get_model("core", "Household")
    Node = apps.get_model("nodes", "Node")
    HouseholdNode = apps.get_model("nodes", "HouseholdNode")

    node, _ = Node.objects.get_or_create(
        key="solace",
        defaults={
            "name": "Solace",
            "description": "Household finances and budgeting.",
            "icon": "coins",
            "is_core": False,
            "is_enabled_by_default": False,
            "supports_kiosk": False,
            "supports_sensitive_lock": True,
        },
    )
    node.supports_kiosk = False
    node.supports_sensitive_lock = True
    node.save(update_fields=["supports_kiosk", "supports_sensitive_lock", "updated_at"])

    household = Household.objects.order_by("id").first()
    if household:
        config, _ = HouseholdNode.objects.get_or_create(
            household=household,
            node=node,
            defaults={"is_enabled": False, "display_order": 12},
        )
        config.requires_reauthentication = True
        config.is_enabled = False
        config.save(update_fields=["requires_reauthentication", "is_enabled", "updated_at"])


def seed_reverse(apps, schema_editor):
    Node = apps.get_model("nodes", "Node")
    node = Node.objects.filter(key="solace").first()
    if node:
        node.supports_sensitive_lock = True
        node.save(update_fields=["supports_sensitive_lock", "updated_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("nodes", "0005_seed_homestead_node"),
        ("core", "0002_seed_household"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
