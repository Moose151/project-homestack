"""Restore the occurrence-based due-before-payday Dashboard widget."""

from django.db import migrations


def forward(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    HouseholdHubWidget = apps.get_model("hub", "HouseholdHubWidget")
    widget = HubWidget.objects.filter(key="solace_bills_due").first()
    if widget is None:
        return
    widget.name = "Due before next payday"
    widget.description = "Unpaid bill occurrences through the household's next payday."
    widget.always_visible = True
    widget.save(update_fields=["name", "description", "always_visible"])
    HouseholdHubWidget.objects.filter(widget=widget).update(is_enabled=True)


def reverse(apps, schema_editor):
    HubWidget = apps.get_model("hub", "HubWidget")
    widget = HubWidget.objects.filter(key="solace_bills_due").first()
    if widget is None:
        return
    widget.name = "Bills due"
    widget.description = "Upcoming unpaid bills."
    widget.always_visible = False
    widget.save(update_fields=["name", "description", "always_visible"])


class Migration(migrations.Migration):
    dependencies = [("hub", "0015_seed_fitness_widget")]
    operations = [migrations.RunPython(forward, reverse)]
