"""Seed the unified "Upcoming" widget and mark the ambient widgets always-visible.

Owner direction, 2026-08-09: the Hub should carry one Upcoming card covering everything
dated, not a permanent card per node. A household does not have vet appointments most
weeks, so a "Vet appointments" card that says "No appointments" for eleven months is a
grid slot spent on nothing.

Two changes:

1. ``HubWidget.always_visible`` — ambient widgets (clock, quick add, daily quote,
   countdown) own no domain data and still render when empty. Every other widget is now
   dropped from the Hub response while it has nothing to show.
2. ``upcoming`` — a core widget (no source node) assembled from calendar events, which
   already mirror every dated node record via the scheduling helper (D7).

For an existing household the per-node dated widgets that Upcoming subsumes are switched
off, since leaving both on would show the same vet appointment twice. They stay in the
catalogue and can be re-enabled from Tune this page. Reverse leaves enablement alone —
re-enabling widgets a household has since curated would be worse than a no-op.
"""
from django.db import migrations, models

# Ambient widgets: no domain data, still worth a slot.
_ALWAYS_VISIBLE = ["clock", "quick_add", "daily_quote", "countdown"]

# Per-node dated widgets that the unified Upcoming card now covers.
_SUBSUMED = [
    "atlas_reminders",
    "calendar_upcoming",
    "education_classes",
    "education_deadlines",
    "education_events",
    "homestead_maintenance",
    "pets_appointments",
    "pets_reminders",
    "solace_bills_due",
]


def seed_forward(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HouseholdHubWidget = apps.get_model("hub", "HouseholdHubWidget")
    Household = apps.get_model("core", "Household")

    HubWidget.objects.filter(key__in=_ALWAYS_VISIBLE).update(always_visible=True)

    widget, _ = HubWidget.objects.get_or_create(
        key="upcoming",
        defaults={
            "name": "Upcoming",
            "description": (
                "Everything dated across the household — reminders, deadlines, "
                "appointments, maintenance and bills — over a choosable horizon."
            ),
            "source_node": None,
            "supports_kiosk": True,
            "display_order": 1,
            "always_visible": False,
        },
    )

    household = Household.objects.order_by("id").first()
    if household is None:
        return

    HouseholdHubWidget.objects.get_or_create(
        household=household,
        widget=widget,
        defaults={"is_enabled": True, "display_order": 1, "size": "medium"},
    )
    HouseholdHubWidget.objects.filter(
        household=household, widget__key__in=_SUBSUMED
    ).update(is_enabled=False)


def seed_reverse(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HubWidget.objects.filter(key="upcoming").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("hub", "0013_seed_countdown_widget"),
        ("core", "0002_seed_household"),
    ]

    operations = [
        migrations.AddField(
            model_name="hubwidget",
            name="always_visible",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Ambient widgets (clock, quick add, countdown) render even with no "
                    "content. Every other widget is dropped from the Hub while it has "
                    "nothing to show."
                ),
            ),
        ),
        migrations.RunPython(seed_forward, seed_reverse),
    ]
