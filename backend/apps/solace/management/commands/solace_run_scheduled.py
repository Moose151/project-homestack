"""Run Solace's idempotent daily reminder job from cron."""
from __future__ import annotations

from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.solace.tasks import send_due_reminders


class Command(BaseCommand):
    help = "Create generic HomeStack reminders for Solace items due soon."

    def add_arguments(self, parser):
        parser.add_argument("--date", help="Override today as YYYY-MM-DD (for testing).")

    def handle(self, *args, **options):
        try:
            on = date.fromisoformat(options["date"]) if options.get("date") else None
        except ValueError as exc:
            raise CommandError(f"Invalid --date: {exc}") from exc
        created = send_due_reminders(on=on)
        self.stdout.write(self.style.SUCCESS(f"Solace reminders created: {created}"))
