"""Run Notifications' idempotent scheduled reminders + countdown digest from cron."""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.notifications.tasks import run_countdown_digest, run_due_reminders


# Recommended host cron (hourly; gates internally on the 23-25h window and each user's own
# morning_time, and is idempotent via NotificationReminderLog so overlapping/missed runs are
# safe):
# 0 * * * * docker exec homestack-backend python manage.py notifications_run_scheduled


class Command(BaseCommand):
    help = "Send due 24h/morning-of reminders and the daily countdown digest."

    def handle(self, *args, **options):
        reminders = run_due_reminders()
        digest = run_countdown_digest()
        self.stdout.write(
            self.style.SUCCESS(
                f"Reminders — 24h: {reminders['24h']}; morning_of: {reminders['morning_of']}. "
                f"Countdown digest sent: {digest['sent']}."
            )
        )
