"""Refresh calendar sources that are due, from cron.

Sources are refreshed here and never during an ordinary Calendar page load: browsing the
calendar must not make the server perform external HTTP requests, both for page speed and
because a slow or hostile feed would then be able to hold a request worker open.

Every step is idempotent — an event is identified by (source, external UID), so a re-run or an
overlapping run updates the same rows rather than duplicating them, and the sync takes a row
lock per source so two concurrent runs serialise. One failing source is recorded on its own row
and does not abort the rest.

Recommended host cron (every few hours is ample for fixture lists and school calendars; the
command itself skips anything refreshed within the interval):
  17 */3 * * * docker exec homestack-backend python manage.py calendar_sync_sources
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.scheduling.sources.sync import sync_due_sources


class Command(BaseCommand):
    help = "Refresh subscribed/automatic calendar sources that are due for a sync."

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval-hours",
            type=int,
            default=6,
            help="Skip sources refreshed successfully within this many hours (default 6).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Refresh every enabled source regardless of when it last succeeded.",
        )

    def handle(self, *args, **options):
        result = sync_due_sources(
            interval_hours=0 if options["force"] else options["interval_hours"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Calendar sources — synced: {result['synced']}; failed: {result['failed']}."
            )
        )
