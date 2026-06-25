"""Meridian scheduled work — run daily by cron (D5: no Celery/in-process scheduler).

Does the periodic jobs the legacy app ran in APScheduler, idempotently:
  * weekly allowance awards (per-person amount on a chosen weekday);
  * perfect-month routine badge (awarded via the achievements event bus).

Streak auto-end needs no job — streaks are computed at read time from the completion history
and the household ``auto_end_streaks`` setting. Recurring-task re-arm is part of the deferred
task-completion model (Phase 2.9b).

Example crontab (run once a day at 06:00):
    0 6 * * *  docker exec homestack-backend python manage.py meridian_run_scheduled
"""
from __future__ import annotations

from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError

from apps.meridian import services


class Command(BaseCommand):
    help = "Run Meridian's daily scheduled jobs (allowance, perfect-month badges)."

    def add_arguments(self, parser):
        parser.add_argument("--date", help="Override 'today' as YYYY-MM-DD (for testing).")
        parser.add_argument("--skip-allowance", action="store_true")
        parser.add_argument("--skip-badges", action="store_true")

    def handle(self, *args, **options):
        if options.get("date"):
            try:
                today = date.fromisoformat(options["date"])
            except ValueError as exc:
                raise CommandError(f"Invalid --date: {exc}")
        else:
            from django.utils import timezone
            today = timezone.localdate()

        if not options["skip_allowance"]:
            n = services.award_allowances(on=today)
            self.stdout.write(self.style.SUCCESS(f"Allowances awarded: {n}"))

        if not options["skip_badges"]:
            # Evaluate this month and (on early days) the previous month, to catch month-end.
            total = services.award_perfect_month_badges(year=today.year, month=today.month)
            prev = (today.replace(day=1) - timedelta(days=1))
            total += services.award_perfect_month_badges(year=prev.year, month=prev.month)
            self.stdout.write(self.style.SUCCESS(f"Perfect-month checks emitted: {total}"))
