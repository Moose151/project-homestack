"""Seed the Calendar "upcoming events" Hub widget (M2.5 A.4 / C).

A core-service widget (source_node = null — Calendar is the `scheduling` core service, not a
node). Content is assembled from scheduling selectors. Kiosk-safe; enabled by default.
"""
from django.db import migrations


def seed_forward(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HouseholdHubWidget = apps.get_model("hub", "HouseholdHubWidget")
    Household = apps.get_model("core", "Household")

    widget, _ = HubWidget.objects.get_or_create(
        key="calendar_upcoming",
        defaults={
            "name": "Upcoming",
            "description": "The next few events on the household calendar.",
            "source_node": None,
            "supports_kiosk": True,
            "display_order": 5,
        },
    )
    household = Household.objects.order_by("id").first()
    if household:
        HouseholdHubWidget.objects.get_or_create(
            household=household, widget=widget,
            defaults={"is_enabled": True, "display_order": 5, "size": "medium"},
        )


def seed_reverse(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HubWidget.objects.filter(key="calendar_upcoming").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("hub", "0004_seed_clock_widget"),
        ("core", "0002_seed_household"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
