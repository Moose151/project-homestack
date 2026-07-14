"""Seed the Education Hub widgets (Node Spec 8).

Per the "every node ships its Hub widget" rule (M2.5 A.3): a node is not done until it
contributes seeded HubWidget rows (source_node = "education") whose content is assembled by
the Hub service via a permission-filtered selector (no cross-node model imports, D4).

- education_deadlines — upcoming, still-open assignments/exams. Enabled by default.
- education_classes   — the timetabled classes/lectures. Enabled by default.

Kiosk support is off for now: the uni-first slice is adult/web-facing; child-facing kiosk
homework cards come in a later Education slice (owner re-prioritisation 2026-07-14).
"""
from django.db import migrations

_WIDGETS = [
    {
        "key": "education_deadlines",
        "name": "Assignments due",
        "description": "Upcoming assignments, exams and homework that are still open.",
        "display_order": 6,
    },
    {
        "key": "education_classes",
        "name": "Classes",
        "description": "Your timetabled classes and lectures.",
        "display_order": 7,
    },
]


def seed_forward(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HouseholdHubWidget = apps.get_model("hub", "HouseholdHubWidget")
    Household = apps.get_model("core", "Household")
    Node = apps.get_model("nodes", "Node")
    household = Household.objects.order_by("id").first()
    node = Node.objects.filter(key="education").first()

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
                household=household, widget=widget,
                defaults={"is_enabled": True, "display_order": w["display_order"], "size": "medium"},
            )


def seed_reverse(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HubWidget.objects.filter(key__in=[w["key"] for w in _WIDGETS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("hub", "0005_seed_calendar_widget"),
        ("core", "0002_seed_household"),
        ("nodes", "0002_seed_nodes"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
