"""reconcile_education_assessment_calendar_events — one-shot repair for stale assignment
CalendarEvents.

Run after deploying the fix to EducationAssessment.get_calendar_data() to remove the
CalendarEvent for every assessment that was already marked complete before the fix
(status DONE/SUBMITTED), which the old code never cleared. Safe to re-run; it only
deletes stale events for completed assessments and recreates missing ones for open
assessments — it never touches assessment rows themselves.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Reconcile every education assessment's CalendarEvent so completed assessments "
        "have no lingering event and open assessments with a due date have one."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing anything.",
        )
        parser.add_argument(
            "--household",
            type=int,
            default=None,
            help="Limit to a single household pk.",
        )

    def handle(self, *args, **options):
        from apps.education.models import EducationAssessment
        from apps.scheduling.helpers import sync_event_for

        dry_run = options["dry_run"]
        qs = EducationAssessment.objects.all()
        if options["household"]:
            qs = qs.filter(household_id=options["household"])

        changed = unchanged = 0
        for assessment in qs.iterator():
            old_event_id = assessment.calendar_event_id
            expected = None if (not assessment.due_at or assessment.is_complete) else "event"
            would_change = bool(old_event_id) != bool(expected)
            if not dry_run:
                sync_event_for(assessment)
            tag = "[dry-run] " if dry_run else ""
            if would_change or (not dry_run and old_event_id != assessment.calendar_event_id):
                changed += 1
                self.stdout.write(
                    f"{tag}Assessment {assessment.pk} ({assessment.title!r}, "
                    f"status={assessment.status}): calendar_event_id={old_event_id} → "
                    f"{assessment.calendar_event_id if not dry_run else expected}"
                )
            else:
                unchanged += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {'Would change' if dry_run else 'Changed'} {changed} assessments, "
                f"{unchanged} already correct."
            )
        )
