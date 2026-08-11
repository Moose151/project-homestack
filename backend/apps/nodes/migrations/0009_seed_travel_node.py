from django.db import migrations


def seed(apps, schema_editor):
    Node = apps.get_model("nodes", "Node")
    HouseholdNode = apps.get_model("nodes", "HouseholdNode")
    node, _ = Node.objects.get_or_create(key="travel", defaults={
        "name": "Travel", "description": "Trips, destination ideas, bookings and preparation.",
        "icon": "plane", "is_enabled_by_default": False, "supports_kiosk": False,
    })
    for household in apps.get_model("core", "Household").objects.all():
        HouseholdNode.objects.get_or_create(household=household, node=node, defaults={"is_enabled": False, "display_order": 14})


def unseed(apps, schema_editor):
    apps.get_model("nodes", "Node").objects.filter(key="travel").delete()


class Migration(migrations.Migration):
    dependencies = [("nodes", "0008_seed_fitness_node"), ("core", "0002_seed_household")]
    operations = [migrations.RunPython(seed, unseed)]
