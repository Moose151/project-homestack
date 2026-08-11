from django.core.management.base import BaseCommand

from apps.link_imports.tasks import run_daily_price_watches


# Recommended host cron (hourly; this command gates on household-local 09:00 and is idempotent):
# 7 * * * * docker exec homestack-backend python manage.py link_imports_run_scheduled


class Command(BaseCommand):
    help = "Run idempotent due product price watches after 09:00 household-local time."

    def handle(self, *args, **options):
        result = run_daily_price_watches()
        self.stdout.write(f"Price watches checked: {result['checked']}; alerts: {result['alerts']}")
