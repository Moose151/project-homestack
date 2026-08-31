"""reconcile_bill_calendar_events — one-shot repair for stale bill CalendarEvents.

Run after deploying the fix to Bill.get_calendar_data() to bring all existing
recurring-bill CalendarEvents up to date with the correct next-occurrence date.
Safe to re-run; it only updates, never deletes, valid bill records.
"""
from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = (
        "Reconcile every active bill's CalendarEvent so it points to the next "
        "UPCOMING occurrence rather than the original stale anchor date."
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
        from apps.scheduling.helpers import sync_event_for
        from apps.solace.bill_schedule import ensure_bill_occurrences
        from apps.solace.models import Bill

        dry_run = options["dry_run"]
        today = timezone.localdate()
        qs = Bill.objects.filter(is_active=True)
        if options["household"]:
            qs = qs.filter(household_id=options["household"])

        updated = skipped = 0
        for bill in qs.iterator():
            old_event_id = bill.calendar_event_id
            if not dry_run:
                ensure_bill_occurrences(
                    bill,
                    today - timedelta(days=90),
                    today + timedelta(days=550),
                )
                sync_event_for(bill)
            tag = "[dry-run] " if dry_run else ""
            self.stdout.write(
                f"{tag}Bill {bill.pk} ({bill.name!r}): "
                f"calendar_event_id={old_event_id} → {bill.calendar_event_id}"
            )
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {'Would process' if dry_run else 'Processed'} {updated} bills, skipped {skipped}."
            )
        )
