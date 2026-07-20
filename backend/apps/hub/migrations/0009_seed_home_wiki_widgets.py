"""Seed the Home Wiki Hub widgets (Node Spec 8).

Per the "every node ships its Hub widget" rule (M2.5 A.3): content is assembled by the Hub
service via permission-filtered selectors (no cross-node model imports, D4).

- wiki_favourites — pinned reference pages (WiFi, bin night, …). Enabled + kiosk-safe.
- wiki_emergency  — shortcut to emergency-info pages. Enabled + kiosk-safe.
- wiki_recent     — recently updated pages. Disabled by default (opt-in), web only.
"""
from django.db import migrations

_WIDGETS = [
    {
        "key": "wiki_favourites",
        "name": "Favourite pages",
        "description": "Pinned Home Wiki pages the household looks up often.",
        "display_order": 9,
        "supports_kiosk": True,
        "enabled": True,
    },
    {
        "key": "wiki_emergency",
        "name": "Emergency info",
        "description": "Quick access to emergency contacts and procedures.",
        "display_order": 10,
        "supports_kiosk": True,
        "enabled": True,
    },
    {
        "key": "wiki_recent",
        "name": "Recently updated",
        "description": "Home Wiki pages changed recently.",
        "display_order": 11,
        "supports_kiosk": False,
        "enabled": False,
    },
]


def seed_forward(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HouseholdHubWidget = apps.get_model("hub", "HouseholdHubWidget")
    Household = apps.get_model("core", "Household")
    Node = apps.get_model("nodes", "Node")
    household = Household.objects.order_by("id").first()
    node = Node.objects.filter(key="home_wiki").first()

    for w in _WIDGETS:
        widget, _ = HubWidget.objects.get_or_create(
            key=w["key"],
            defaults={
                "name": w["name"],
                "description": w["description"],
                "source_node": node,
                "supports_kiosk": w["supports_kiosk"],
                "display_order": w["display_order"],
            },
        )
        if household:
            HouseholdHubWidget.objects.get_or_create(
                household=household, widget=widget,
                defaults={"is_enabled": w["enabled"], "display_order": w["display_order"], "size": "medium"},
            )


def seed_reverse(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HubWidget.objects.filter(key__in=[w["key"] for w in _WIDGETS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("hub", "0008_seed_education_events_widget"),
        ("core", "0002_seed_household"),
        ("nodes", "0002_seed_nodes"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
