"""Enable the Meridian node for the household (Milestone 2).

The node catalogue row + a disabled HouseholdNode were seeded in nodes/0002. Now that
Meridian is built end-to-end, flip it on for the single household. Idempotent.
"""
from django.db import migrations


def enable_forward(apps, schema_editor):
    Household = apps.get_model("core", "Household")
    Node = apps.get_model("nodes", "Node")
    HouseholdNode = apps.get_model("nodes", "HouseholdNode")

    household = Household.objects.order_by("id").first()
    node = Node.objects.filter(key="meridian").first()
    if not household or not node:
        return

    hn, _ = HouseholdNode.objects.get_or_create(
        household=household, node=node, defaults={"is_enabled": True}
    )
    if not hn.is_enabled:
        hn.is_enabled = True
        hn.save(update_fields=["is_enabled"])


def enable_reverse(apps, schema_editor):
    Household = apps.get_model("core", "Household")
    Node = apps.get_model("nodes", "Node")
    HouseholdNode = apps.get_model("nodes", "HouseholdNode")

    household = Household.objects.order_by("id").first()
    node = Node.objects.filter(key="meridian").first()
    if household and node:
        HouseholdNode.objects.filter(household=household, node=node).update(is_enabled=False)


class Migration(migrations.Migration):
    dependencies = [
        ("meridian", "0001_initial"),
        ("nodes", "0002_seed_nodes"),
    ]

    operations = [
        migrations.RunPython(enable_forward, enable_reverse),
    ]
