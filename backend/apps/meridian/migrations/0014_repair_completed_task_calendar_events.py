from django.db import migrations


def remove_completed_task_events(apps, schema_editor):
    """Drop Calendar projections left behind by completed one-off tasks.

    Before this release a completed MeridianTask kept its deadline projection, so finished
    work stayed on the Dashboard as permanently overdue. Recurring tasks are excluded: their
    projection is the recurring deadline, and `status` is only recomputed on write.
    """
    MeridianTask = apps.get_model("meridian", "MeridianTask")
    CalendarEvent = apps.get_model("scheduling", "CalendarEvent")

    stale_ids = list(
        MeridianTask.objects.filter(status__in=["pending", "approved"], recurrence_rule="")
        .exclude(calendar_event_id=None)
        .values_list("id", flat=True)
    )
    if not stale_ids:
        return

    CalendarEvent.objects.filter(
        source_record_type="MeridianTask",
        source_record_id__in=stale_ids,
    ).delete()
    MeridianTask.objects.filter(id__in=stale_ids).update(calendar_event_id=None)


class Migration(migrations.Migration):
    dependencies = [
        ("meridian", "0013_multi_person_assignment"),
        ("scheduling", "0006_calendar_sources"),
    ]

    operations = [
        migrations.RunPython(remove_completed_task_events, migrations.RunPython.noop),
    ]
