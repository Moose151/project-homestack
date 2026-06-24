"""Seed Meridian hub widgets and enable them for the household (Milestone 2, Node Spec 8).

Kiosk-safe (kid-facing):  my_tasks, hot_tasks, points_summary
Web only (parent-facing):  pending_approvals, reward_requests
Achievements are deferred (future Meridian work) and not seeded yet.
"""
from django.db import migrations

_WIDGETS = [
    {"key": "meridian_my_tasks", "name": "My Tasks",
     "description": "Tasks you can complete for points.",
     "supports_kiosk": True, "display_order": 10},
    {"key": "meridian_hot_tasks", "name": "Hot Tasks",
     "description": "Featured tasks worth grabbing now.",
     "supports_kiosk": True, "display_order": 11},
    {"key": "meridian_points", "name": "Points",
     "description": "Points earned across the household.",
     "supports_kiosk": True, "display_order": 12},
    {"key": "meridian_pending_approvals", "name": "Pending Approvals",
     "description": "Completed tasks awaiting your approval.",
     "supports_kiosk": False, "display_order": 13},
    {"key": "meridian_reward_requests", "name": "Reward Requests",
     "description": "Reward redemptions awaiting approval.",
     "supports_kiosk": False, "display_order": 14},
]


def seed_forward(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HouseholdHubWidget = apps.get_model("hub", "HouseholdHubWidget")
    Household = apps.get_model("core", "Household")
    Node = apps.get_model("nodes", "Node")

    household = Household.objects.order_by("id").first()
    node = Node.objects.filter(key="meridian").first()

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
                household=household,
                widget=widget,
                defaults={"is_enabled": True, "display_order": w["display_order"]},
            )


def seed_reverse(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HubWidget.objects.filter(key__in=[w["key"] for w in _WIDGETS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("hub", "0002_seed_hub_widgets"),
        ("nodes", "0002_seed_nodes"),
        ("core", "0002_seed_household"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
