from django.db import migrations


def remove_completed_assessment_events(apps, schema_editor):
    """Remove stale Calendar projections left by pre-0.40.3 completion writes."""
    EducationAssessment = apps.get_model("education", "EducationAssessment")
    CalendarEvent = apps.get_model("scheduling", "CalendarEvent")

    completed_ids = list(
        EducationAssessment.objects.filter(status__in=["submitted", "done"])
        .values_list("id", flat=True)
    )
    if not completed_ids:
        return

    CalendarEvent.objects.filter(
        source_record_type="EducationAssessment",
        source_record_id__in=completed_ids,
    ).delete()
    EducationAssessment.objects.filter(id__in=completed_ids).update(calendar_event_id=None)


class Migration(migrations.Migration):
    dependencies = [
        ("education", "0007_educationclasssession_series_key"),
        ("scheduling", "0006_calendar_sources"),
    ]

    operations = [
        migrations.RunPython(remove_completed_assessment_events, migrations.RunPython.noop),
    ]
