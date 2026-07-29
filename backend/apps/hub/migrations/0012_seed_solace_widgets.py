"""Seed Solace Hub widgets.

Finance widgets are web-only and still protected by Solace permissions plus re-auth in the
Solace APIs. The Hub service also suppresses them unless the user has Solace view access.
"""
from django.db import migrations

_WIDGETS = [
    {
        "key": "solace_bills_due",
        "name": "Bills due",
        "description": "Upcoming unpaid bills.",
        "display_order": 17,
    },
    {
        "key": "solace_subscriptions",
        "name": "Subscriptions",
        "description": "Upcoming subscription renewals.",
        "display_order": 18,
    },
    {
        "key": "solace_planned_purchases",
        "name": "Planned purchases",
        "description": "Open planned purchases and set-asides.",
        "display_order": 19,
    },
]


def seed_forward(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HouseholdHubWidget = apps.get_model("hub", "HouseholdHubWidget")
    Household = apps.get_model("core", "Household")
    Node = apps.get_model("nodes", "Node")
    household = Household.objects.order_by("id").first()
    node = Node.objects.filter(key="solace").first()

    for w in _WIDGETS:
        widget, _ = HubWidget.objects.get_or_create(
            key=w["key"],
            defaults={
                "name": w["name"],
                "description": w["description"],
                "source_node": node,
                "supports_kiosk": False,
                "display_order": w["display_order"],
            },
        )
        if household:
            HouseholdHubWidget.objects.get_or_create(
                household=household,
                widget=widget,
                defaults={"is_enabled": True, "display_order": w["display_order"], "size": "medium"},
            )


def seed_reverse(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HubWidget.objects.filter(key__in=[w["key"] for w in _WIDGETS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("hub", "0011_seed_homestead_widgets"),
        ("core", "0002_seed_household"),
        ("nodes", "0006_configure_solace_sensitive"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
