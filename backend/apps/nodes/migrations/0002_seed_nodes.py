"""
Seed all 12 node catalogue rows and create per-household HouseholdNode config rows.

atlas → is_enabled=True (is_core=True, the walking-skeleton node per D18).
All other nodes → is_enabled=False (enabled later per household choice).
"""
from django.db import migrations

_NODES = [
    {"key": "atlas",      "name": "Atlas",       "description": "Lists, notes and reminders.",
     "icon": "clipboard-list", "is_core": True,  "is_enabled_by_default": True,
     "supports_kiosk": True,  "supports_sensitive_lock": False},
    {"key": "home_wiki",  "name": "Home Wiki",   "description": "Knowledge base for the home.",
     "icon": "book-open",      "is_core": False, "is_enabled_by_default": False,
     "supports_kiosk": False, "supports_sensitive_lock": False},
    {"key": "pets",       "name": "Pets",        "description": "Pet health and care tracking.",
     "icon": "paw-print",      "is_core": False, "is_enabled_by_default": False,
     "supports_kiosk": True,  "supports_sensitive_lock": False},
    {"key": "education",  "name": "Education",   "description": "Homework, reading and learning.",
     "icon": "graduation-cap", "is_core": False, "is_enabled_by_default": False,
     "supports_kiosk": True,  "supports_sensitive_lock": False},
    {"key": "inventory",  "name": "Inventory",   "description": "Household consumables and stock.",
     "icon": "package",        "is_core": False, "is_enabled_by_default": False,
     "supports_kiosk": False, "supports_sensitive_lock": False},
    {"key": "assets",     "name": "Assets",      "description": "High-value items and documents.",
     "icon": "briefcase",      "is_core": False, "is_enabled_by_default": False,
     "supports_kiosk": False, "supports_sensitive_lock": True},
    {"key": "hearth",     "name": "Hearth",      "description": "Meals, chores and home routines.",
     "icon": "home",           "is_core": False, "is_enabled_by_default": False,
     "supports_kiosk": True,  "supports_sensitive_lock": False},
    {"key": "travel",     "name": "Travel",      "description": "Trip planning and itineraries.",
     "icon": "plane",          "is_core": False, "is_enabled_by_default": False,
     "supports_kiosk": False, "supports_sensitive_lock": False},
    {"key": "projects",   "name": "Projects",    "description": "Home improvement and longer tasks.",
     "icon": "tool",           "is_core": False, "is_enabled_by_default": False,
     "supports_kiosk": False, "supports_sensitive_lock": False},
    {"key": "health",     "name": "Health",      "description": "Medical records and appointments.",
     "icon": "heart-pulse",    "is_core": False, "is_enabled_by_default": False,
     "supports_kiosk": False, "supports_sensitive_lock": True},
    {"key": "meridian",   "name": "Meridian",    "description": "Chores and rewards for children.",
     "icon": "star",           "is_core": False, "is_enabled_by_default": False,
     "supports_kiosk": True,  "supports_sensitive_lock": False},
    {"key": "solace",     "name": "Solace",      "description": "Household finances and budgeting.",
     "icon": "coins",          "is_core": False, "is_enabled_by_default": False,
     "supports_kiosk": False, "supports_sensitive_lock": True},
]


def seed_forward(apps, schema_editor):
    Household = apps.get_model("core", "Household")
    Node = apps.get_model("nodes", "Node")
    HouseholdNode = apps.get_model("nodes", "HouseholdNode")

    # Seed node catalogue
    for i, data in enumerate(_NODES):
        node, _ = Node.objects.get_or_create(
            key=data["key"],
            defaults={k: v for k, v in data.items() if k != "key"},
        )

    household = Household.objects.order_by("id").first()
    if not household:
        return

    # Create HouseholdNode rows: atlas enabled, rest disabled
    for i, data in enumerate(_NODES):
        node = Node.objects.get(key=data["key"])
        HouseholdNode.objects.get_or_create(
            household=household,
            node=node,
            defaults={
                "is_enabled": data["key"] == "atlas",
                "display_order": i,
            },
        )


def seed_reverse(apps, schema_editor):
    Node = apps.get_model("nodes", "Node")
    Node.objects.filter(key__in=[d["key"] for d in _NODES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("nodes", "0001_initial"),
        ("core", "0002_seed_household"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
