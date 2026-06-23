"""Seed the single household row (D1). Idempotent and generic — no household specifics (D15)."""
from django.db import migrations

HOUSEHOLD_DEFAULTS = {
    "name": "HomeStack Household",  # generic placeholder; editable in Settings later
    "slug": "homestack",
    "timezone": "UTC",
    "default_locale": "en-us",
}


def seed_household(apps, schema_editor):
    Household = apps.get_model("core", "Household")
    if not Household.objects.exists():
        Household.objects.create(**HOUSEHOLD_DEFAULTS)


def unseed_household(apps, schema_editor):
    # No-op on reverse: the household may own rows (PROTECT); don't delete on rollback.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_household, unseed_household),
    ]
