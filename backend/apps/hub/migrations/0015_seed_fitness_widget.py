from django.db import migrations


def seed_forward(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HouseholdHubWidget = apps.get_model("hub", "HouseholdHubWidget")
    household = apps.get_model("core", "Household").objects.order_by("id").first()
    node = apps.get_model("nodes", "Node").objects.filter(key="fitness").first()
    widget, _ = HubWidget.objects.get_or_create(key="fitness_recent", defaults={
        "name": "Recent training", "description": "Completed household workouts and new personal bests.",
        "source_node": node, "supports_kiosk": False, "display_order": 30,
    })
    if household:
        HouseholdHubWidget.objects.get_or_create(
            household=household, widget=widget,
            defaults={"is_enabled": True, "display_order": 30, "size": "medium"},
        )


def seed_reverse(apps, schema_editor):
    apps.get_model("hub", "HubWidget").objects.filter(key="fitness_recent").delete()


class Migration(migrations.Migration):
    dependencies = [("hub", "0014_upcoming_widget_and_always_visible"), ("nodes", "0008_seed_fitness_node")]
    operations = [migrations.RunPython(seed_forward, seed_reverse)]

