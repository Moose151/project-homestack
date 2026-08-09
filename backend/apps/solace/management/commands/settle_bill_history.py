"""One-off repair: settle the arrears that backdated bills arrived with before v0.23.5.

Entering a bill with its real first due date used to backfill every month since as *unpaid*,
so a household that correctly said "this started in 2021" got years of overdue warnings for
money it had actually paid, and an unpaid total and finance health to match. Bills created
from v0.23.5 onward settle their history at entry; this command fixes the ones already saved.

Dry run by default — it prints what it would change and touches nothing. Pass --apply to write.

    python manage.py settle_bill_history
    python manage.py settle_bill_history --apply

Only occurrences that are still `upcoming` and fell due before the bill was entered are
settled. Anything due since you entered the bill is a real payment you may still owe, and is
left alone; so is anything already marked paid or skipped.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import models, transaction
from django.utils import timezone

from apps.solace.models import Bill, BillOccurrence


class Command(BaseCommand):
    help = "Mark pre-existing unpaid occurrences on backdated bills as paid (dry run by default)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write the changes. Without this the command only reports.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        total = 0
        touched_bills = 0

        for bill in Bill.objects.order_by("name"):
            # "Before the bill was entered" — not "before today". A payment that came due after
            # you recorded the bill is one you were tracking, so it stays as it is.
            stale = BillOccurrence.objects.filter(
                bill=bill,
                status=BillOccurrence.Status.UPCOMING,
                due_at__lt=bill.created_at,
            )
            count = stale.count()
            if not count:
                continue

            touched_bills += 1
            total += count
            oldest = stale.order_by("due_at").first()
            self.stdout.write(
                f"  {bill.name}: {count} occurrence(s) from {oldest.due_at:%Y-%m-%d}"
            )
            if apply_changes:
                with transaction.atomic():
                    stale.update(
                        status=BillOccurrence.Status.PAID,
                        paid_at=models.F("due_at"),
                        updated_at=timezone.now(),
                    )

        if not total:
            self.stdout.write(self.style.SUCCESS("Nothing to settle — no bill has stale arrears."))
            return

        summary = f"{total} occurrence(s) across {touched_bills} bill(s)"
        if apply_changes:
            self.stdout.write(self.style.SUCCESS(f"Settled {summary}."))
        else:
            self.stdout.write(self.style.WARNING(
                f"Would settle {summary}. Re-run with --apply to write the changes."
            ))
