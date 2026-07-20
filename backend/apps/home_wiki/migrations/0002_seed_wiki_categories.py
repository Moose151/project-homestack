"""Seed the suggested default Home Wiki categories (Node Spec 6).

Idempotent (get_or_create by household + name). Admins can add/edit/hide/reorder afterwards.
"""
from django.db import migrations

_CATEGORIES = [
    ("Emergency", "#E4572E", "alert-triangle"),
    ("Internet & Technology", "#4C6EF5", "wifi"),
    ("Utilities", "#F59F00", "zap"),
    ("Appliances", "#7048E8", "washing-machine"),
    ("Household Procedures", "#0CA678", "list-checks"),
    ("Cleaning", "#20C997", "spray-can"),
    ("Pets", "#F783AC", "paw-print"),
    ("School", "#5C7CFA", "graduation-cap"),
    ("Contacts", "#845EF7", "contact"),
    ("House Sitting", "#94D82D", "home"),
    ("Manuals", "#868E96", "book-open"),
    ("Miscellaneous", "#ADB5BD", "shapes"),
]


def seed_forward(apps, schema_editor):
    WikiCategory = apps.get_model("home_wiki", "WikiCategory")
    Household = apps.get_model("core", "Household")
    household = Household.objects.order_by("id").first()
    if not household:
        return
    for order, (name, colour, icon) in enumerate(_CATEGORIES):
        WikiCategory.objects.get_or_create(
            household=household, name=name,
            defaults={"colour": colour, "icon": icon, "display_order": order},
        )


def seed_reverse(apps, schema_editor):
    WikiCategory = apps.get_model("home_wiki", "WikiCategory")
    WikiCategory.objects.filter(name__in=[c[0] for c in _CATEGORIES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("home_wiki", "0001_initial"),
        ("core", "0002_seed_household"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
