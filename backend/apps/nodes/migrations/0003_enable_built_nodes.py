"""Enable the built stacks for the household so they show in the node-driven nav.

Atlas was enabled by the seed migration; Meridian and Education are built and in daily
use, so enable them too. Admins can still toggle any stack on/off from the Stacks admin
screen (nodes enable/disable API). Unbuilt nodes stay disabled.
"""
from django.db import migrations

_ENABLE = ["meridian", "education"]


def enable_forward(apps, schema_editor):
    Node = apps.get_model("nodes", "Node")
    HouseholdNode = apps.get_model("nodes", "HouseholdNode")
    Household = apps.get_model("core", "Household")

    household = Household.objects.order_by("id").first()
    if household is None:
        return
    for key in _ENABLE:
        node = Node.objects.filter(key=key).first()
        if node is None:
            continue
        hn, _ = HouseholdNode.objects.get_or_create(
            household=household, node=node, defaults={"is_enabled": True}
        )
        if not hn.is_enabled:
            hn.is_enabled = True
            hn.save(update_fields=["is_enabled", "updated_at"])


def enable_reverse(apps, schema_editor):
    # Non-destructive: leave enablement as-is on reverse.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("nodes", "0002_seed_nodes"),
        ("core", "0002_seed_household"),
    ]

    operations = [
        migrations.RunPython(enable_forward, enable_reverse),
    ]
