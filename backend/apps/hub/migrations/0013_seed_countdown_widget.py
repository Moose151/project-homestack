"""Seed the configurable household countdown widget."""
from django.db import migrations


def seed_forward(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HubWidget.objects.get_or_create(
        key="countdown",
        defaults={
            "name": "Countdown",
            "description": "Count down the days to a date that matters to your household.",
            "source_node": None,
            "supports_kiosk": False,
            "display_order": 35,
        },
    )


def seed_reverse(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HubWidget.objects.filter(key="countdown").delete()


class Migration(migrations.Migration):
    dependencies = [("hub", "0012_seed_solace_widgets")]
    operations = [migrations.RunPython(seed_forward, seed_reverse)]
