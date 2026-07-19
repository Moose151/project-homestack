"""Seed Hub v2 core widgets: notifications summary, quick add, daily quote (Hub UX pass).

All three are core (source_node = null) — they own no domain data. `notifications_summary`
reads the Notifications service; `quick_add` and `daily_quote` render client-side.
Notifications + quick-add are enabled by default (genuinely useful "today" surface); the
ambient `daily_quote` is seeded but left disabled so households opt in.
"""
from django.db import migrations


WIDGETS = [
    {
        "key": "notifications_summary",
        "name": "Notifications",
        "description": "Your unread notifications at a glance.",
        "supports_kiosk": False,
        "display_order": 5,
        "enable": True,
        "size": "small",
    },
    {
        "key": "quick_add",
        "name": "Quick add",
        "description": "Jot a reminder or note without leaving the Hub.",
        "supports_kiosk": False,
        "display_order": 1,
        "enable": True,
        "size": "medium",
    },
    {
        "key": "daily_quote",
        "name": "Thought for the day",
        "description": "A small daily lift for the household noticeboard.",
        "supports_kiosk": True,
        "display_order": 90,
        "enable": False,
        "size": "small",
    },
]


def seed_forward(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HouseholdHubWidget = apps.get_model("hub", "HouseholdHubWidget")
    Household = apps.get_model("core", "Household")
    household = Household.objects.order_by("id").first()

    for spec in WIDGETS:
        widget, _ = HubWidget.objects.get_or_create(
            key=spec["key"],
            defaults={
                "name": spec["name"],
                "description": spec["description"],
                "source_node": None,
                "supports_kiosk": spec["supports_kiosk"],
                "display_order": spec["display_order"],
            },
        )
        if household and spec["enable"]:
            HouseholdHubWidget.objects.get_or_create(
                household=household, widget=widget,
                defaults={
                    "is_enabled": True,
                    "display_order": spec["display_order"],
                    "size": spec["size"],
                },
            )


def seed_reverse(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HubWidget.objects.filter(key__in=[w["key"] for w in WIDGETS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("hub", "0006_seed_education_widgets"),
        ("core", "0002_seed_household"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
