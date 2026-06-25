"""Seed the ambient Clock widget (M2.5 A.4).

A non-node "ambient" widget (source_node = null): rendered entirely client-side, holds no
domain data. Demonstrates the ambient-widget path from `23_Core_Hub.md` §6. Kiosk-safe.
Enabled for the household by default so the Hub feels like a dashboard out of the box.
"""
from django.db import migrations


def seed_forward(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HouseholdHubWidget = apps.get_model("hub", "HouseholdHubWidget")
    Household = apps.get_model("core", "Household")

    widget, _ = HubWidget.objects.get_or_create(
        key="clock",
        defaults={
            "name": "Clock",
            "description": "The current time and date.",
            "source_node": None,
            "supports_kiosk": True,
            "display_order": 0,
        },
    )
    household = Household.objects.order_by("id").first()
    if household:
        HouseholdHubWidget.objects.get_or_create(
            household=household, widget=widget,
            defaults={"is_enabled": True, "display_order": 0, "size": "small"},
        )


def seed_reverse(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HubWidget.objects.filter(key="clock").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("hub", "0003_seed_meridian_widgets"),
        ("core", "0002_seed_household"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
