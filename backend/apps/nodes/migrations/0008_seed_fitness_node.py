from django.db import migrations


def seed_forward(apps, schema_editor):
    Household = apps.get_model("core", "Household")
    Node = apps.get_model("nodes", "Node")
    HouseholdNode = apps.get_model("nodes", "HouseholdNode")
    node, _ = Node.objects.get_or_create(key="fitness", defaults={
        "name": "Fitness", "description": "Training programs, workouts and personal records.",
        "icon": "dumbbell", "is_core": False, "is_enabled_by_default": False,
        "supports_kiosk": False, "supports_sensitive_lock": False,
    })
    household = Household.objects.order_by("id").first()
    if household:
        HouseholdNode.objects.get_or_create(
            household=household, node=node,
            defaults={"is_enabled": False, "display_order": 13},
        )


def seed_reverse(apps, schema_editor):
    apps.get_model("nodes", "Node").objects.filter(key="fitness").delete()


class Migration(migrations.Migration):
    dependencies = [("nodes", "0007_homestead_sensitive_lock"), ("core", "0002_seed_household")]
    operations = [migrations.RunPython(seed_forward, seed_reverse)]
