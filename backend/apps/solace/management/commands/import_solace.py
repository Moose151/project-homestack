"""Management command: import_solace (D14 — one-time native migration).

Imports from the standalone Project Solace SQLite database into the native Solace node.
The command is idempotent by natural keys and dry-runnable.

Usage
-----
    python manage.py import_solace --sqlite-db /home/moose/Documents/project-solace/instance/solace.db --dry-run
    python manage.py import_solace --sqlite-db /home/moose/Documents/project-solace/instance/solace.db
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.core.models import get_active_household
from apps.solace.models import Bill, BudgetBucket, Payday, PaydayChecklistItem, PlannedPurchase, Subscription
from apps.solace.services import (
    create_bill,
    create_bucket,
    create_checklist_item,
    create_payday,
    create_purchase,
    create_subscription,
)

DEFAULT_DB = "/home/moose/Documents/project-solace/instance/solace.db"


@dataclass
class LegacyData:
    categories: dict[int, str]
    bills: list[dict[str, Any]]
    occurrences: dict[int, list[dict[str, Any]]]
    purchases: list[dict[str, Any]]
    buckets: list[dict[str, Any]]
    incomes: list[dict[str, Any]]
    checklist: list[dict[str, Any]]


def _rows(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    return [dict(row) for row in conn.execute(f"select * from {table}")]


def _money(value) -> Decimal:
    return Decimal(str(value or "0")).quantize(Decimal("0.01"))


def _bool(value) -> bool:
    return bool(int(value or 0))


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _parse_dt(value: str | None):
    if not value:
        return None
    text = str(value)
    try:
        if "T" in text or " " in text:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        else:
            d = date.fromisoformat(text[:10])
            dt = datetime.combine(d, time.min)
    except ValueError:
        return None
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _rrule_from_legacy(row: dict[str, Any]) -> str:
    frequency = (row.get("frequency") or "").strip()
    due_day = int(row.get("due_day") or 1)
    due_month = row.get("due_month")
    if frequency == "Weekly":
        return "FREQ=WEEKLY"
    if frequency == "Fortnightly":
        return "FREQ=WEEKLY;INTERVAL=2"
    if frequency == "Monthly":
        return f"FREQ=MONTHLY;BYMONTHDAY={due_day}"
    if frequency == "Quarterly":
        return f"FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY={due_day}"
    if frequency == "Six-monthly":
        return f"FREQ=MONTHLY;INTERVAL=6;BYMONTHDAY={due_day}"
    if frequency == "Yearly":
        bits = ["FREQ=YEARLY", f"BYMONTHDAY={due_day}"]
        if due_month:
            bits.append(f"BYMONTH={int(due_month)}")
        return ";".join(bits)
    return ""


def _next_occurrence(row: dict[str, Any], occurrences: list[dict[str, Any]]):
    today = timezone.localdate()
    upcoming = [
        occ for occ in occurrences
        if (occ.get("status") or "Upcoming") == "Upcoming"
        and (_parse_date(occ.get("due_date")) or date.min) >= today
    ]
    if upcoming:
        upcoming.sort(key=lambda occ: occ.get("due_date") or "")
        return _parse_dt(upcoming[0].get("due_date"))
    return _parse_dt(row.get("start_date"))


def _latest_paid_at(occurrences: list[dict[str, Any]]):
    paid = [occ for occ in occurrences if (occ.get("status") or "") == "Paid" and occ.get("paid_date")]
    if not paid:
        return None
    paid.sort(key=lambda occ: occ.get("paid_date") or "", reverse=True)
    return _parse_dt(paid[0].get("paid_date"))


def _purchase_status(value: str | None) -> str:
    return {
        "Active": "saving",
        "Purchased": "bought",
        "Paused": "idea",
        "Cancelled": "cancelled",
    }.get(value or "", "saving")


def _priority(value: str | None) -> str:
    v = (value or "Medium").lower()
    return v if v in {"low", "medium", "high"} else "medium"


def _billing_cycle(value: str | None) -> str:
    return {
        "Weekly": "weekly",
        "Fortnightly": "fortnightly",
        "Monthly": "monthly",
        "Quarterly": "quarterly",
        "Six-monthly": "other",
        "Yearly": "yearly",
    }.get(value or "", "other")


def _category_name(categories: dict[int, str], value) -> str:
    try:
        key = int(value)
    except (TypeError, ValueError):
        return ""
    return categories.get(key, "")


def _load_legacy(path: Path) -> LegacyData:
    if not path.exists():
        raise CommandError(f"Legacy SQLite database not found: {path}")
    conn = sqlite3.connect(path)
    try:
        categories = {int(r["id"]): r["name"] for r in _rows(conn, "category")}
        occ: dict[int, list[dict[str, Any]]] = {}
        for row in _rows(conn, "bill_occurrence"):
            occ.setdefault(int(row["recurring_bill_id"]), []).append(row)
        return LegacyData(
            categories=categories,
            bills=_rows(conn, "recurring_bill"),
            occurrences=occ,
            purchases=_rows(conn, "planned_purchase"),
            buckets=_rows(conn, "bucket"),
            incomes=_rows(conn, "income_source"),
            checklist=_rows(conn, "payday_checklist_item"),
        )
    except sqlite3.Error as exc:
        raise CommandError(f"Could not read legacy Solace database: {exc}")
    finally:
        conn.close()


class Command(BaseCommand):
    help = "Import standalone Project Solace SQLite data into the native Solace node. Dry-runnable."

    def add_arguments(self, parser):
        parser.add_argument("--sqlite-db", default=DEFAULT_DB, help="Path to legacy Project Solace SQLite DB.")
        parser.add_argument("--dry-run", action="store_true", help="Report what would be imported without writing.")

    def handle(self, *args, **options):
        household = get_active_household()
        if household is None:
            raise CommandError("No active household. Run migrations first.")

        data = _load_legacy(Path(options["sqlite_db"]))
        dry = options["dry_run"]
        self.stdout.write(self.style.WARNING("DRY-RUN — no changes written" if dry else "Importing"))

        try:
            with transaction.atomic():
                stats = self._import(data)
                if dry:
                    transaction.set_rollback(True)
        except Exception as exc:
            raise CommandError(f"Import failed (no changes committed): {exc}")

        for label, n in stats.items():
            self.stdout.write(f"  {label}: {n}")
        self.stdout.write(self.style.SUCCESS("Dry-run complete." if dry else "Import complete."))

    def _import(self, data: LegacyData) -> dict[str, int]:
        stats = {
            "bills": 0,
            "subscriptions": 0,
            "paydays": 0,
            "planned_purchases": 0,
            "buckets": 0,
            "bucket_rules_enriched": 0,
            "checklist_items": 0,
            "skipped_inactive": 0,
        }
        system_user = None

        for row in data.bills:
            if not _bool(row.get("active")):
                stats["skipped_inactive"] += 1
                continue
            category = _category_name(data.categories, row.get("category_id"))
            occurrences = data.occurrences.get(int(row["id"]), [])
            due_at = _next_occurrence(row, occurrences)
            common = {
                "provider": row.get("account_name") or "",
                "amount": _money(row.get("amount")),
                "recurrence_rule": _rrule_from_legacy(row),
                "notes": row.get("notes") or "",
            }
            if category.lower() == "subscriptions":
                if Subscription.objects.filter(name=row["name"]).exists():
                    continue
                create_subscription(
                    system_user,
                    name=row["name"],
                    billing_cycle=_billing_cycle(row.get("frequency")),
                    next_renewal_at=due_at,
                    is_active=True,
                    **common,
                )
                stats["subscriptions"] += 1
            else:
                if Bill.objects.filter(name=row["name"]).exists():
                    continue
                create_bill(
                    system_user,
                    name=row["name"],
                    category=_bill_category(category),
                    due_at=due_at,
                    is_paid=False,
                    paid_at=_latest_paid_at(occurrences),
                    **common,
                )
                stats["bills"] += 1

        for row in data.incomes:
            if not _bool(row.get("active")):
                stats["skipped_inactive"] += 1
                continue
            title = f"{row.get('owner_name') or 'Household'}: {row.get('name') or 'Income'}"
            if Payday.objects.filter(title=title).exists():
                continue
            create_payday(
                system_user,
                title=title,
                expected_amount=_money(row.get("amount")),
                pay_at=_parse_dt(row.get("next_pay_date")),
                recurrence_rule="FREQ=WEEKLY;INTERVAL=2",
                notes=row.get("notes") or f"Imported from legacy income source #{row['id']}.",
            )
            stats["paydays"] += 1

        for row in data.purchases:
            if PlannedPurchase.objects.filter(name=row["name"]).exists():
                continue
            create_purchase(
                system_user,
                name=row["name"],
                category=_category_name(data.categories, row.get("category_id")),
                target_amount=_money(row.get("target_amount")),
                saved_amount=_money(row.get("amount_saved")),
                target_date=_parse_dt(row.get("target_date")),
                status=_purchase_status(row.get("status")),
                priority=_priority(row.get("priority")),
                notes=row.get("notes") or "",
            )
            stats["planned_purchases"] += 1

        for row in data.buckets:
            if not _bool(row.get("active")):
                stats["skipped_inactive"] += 1
                continue
            if BudgetBucket.objects.filter(name=row["name"]).exists():
                existing = BudgetBucket.objects.get(name=row["name"])
                if existing.allocation_value == 0:
                    fixed = row.get("fixed_amount")
                    existing.allocation_method = (
                        BudgetBucket.AllocationMethod.FIXED
                        if fixed not in (None, "")
                        else BudgetBucket.AllocationMethod.PERCENTAGE
                    )
                    existing.allocation_value = _money(
                        fixed if fixed not in (None, "") else row.get("percentage")
                    )
                    existing.rounding_increment = _money(row.get("rounding_increment") or 1)
                    existing.cap_to_remaining = _bool(row.get("cap_to_remaining"))
                    existing.position = int(row.get("sort_order") or 0)
                    existing.save(
                        update_fields=[
                            "allocation_method",
                            "allocation_value",
                            "rounding_increment",
                            "cap_to_remaining",
                            "position",
                            "updated_at",
                        ]
                    )
                    stats["bucket_rules_enriched"] += 1
                continue
            fixed = row.get("fixed_amount")
            notes = (
                f"Imported bucket rule: {row.get('percentage') or 0}% of pay; "
                f"fixed amount {fixed or 'none'}; rounding ${row.get('rounding_increment')}; "
                f"cap to remaining: {'yes' if _bool(row.get('cap_to_remaining')) else 'no'}."
            )
            if row.get("notes"):
                notes = f"{notes}\n\n{row['notes']}"
            create_bucket(
                system_user,
                name=row["name"],
                category=row.get("bucket_type") or "",
                target_amount=Decimal("0.00"),
                current_amount=Decimal("0.00"),
                allocation_method=(
                    BudgetBucket.AllocationMethod.FIXED
                    if fixed not in (None, "")
                    else BudgetBucket.AllocationMethod.PERCENTAGE
                ),
                allocation_value=_money(
                    fixed if fixed not in (None, "") else row.get("percentage")
                ),
                rounding_increment=_money(row.get("rounding_increment") or 1),
                cap_to_remaining=_bool(row.get("cap_to_remaining")),
                position=int(row.get("sort_order") or 0),
                notes=notes,
            )
            stats["buckets"] += 1

        latest_cycle = max((row.get("cycle_start") or "" for row in data.checklist), default="")
        for row in data.checklist:
            if row.get("cycle_start") != latest_cycle:
                continue
            title = row.get("label") or row.get("item_key") or "Checklist item"
            if PaydayChecklistItem.objects.filter(title=title, position=int(row.get("sort_order") or 0)).exists():
                continue
            create_checklist_item(
                system_user,
                title=title,
                cycle_start=_parse_date(latest_cycle),
                source_key=row.get("item_key") or "",
                amount_hint=_money(row.get("amount")),
                position=int(row.get("sort_order") or 0),
                is_complete=_bool(row.get("completed")),
                completed_at=_parse_dt(row.get("completed_at")),
                notes=f"Imported from legacy cycle {latest_cycle}; key {row.get('item_key') or ''}.",
            )
            stats["checklist_items"] += 1

        return stats


def _bill_category(category_name: str) -> str:
    name = (category_name or "").lower()
    if "mortgage" in name or "rent" in name or "house" in name:
        return "mortgage"
    if "insurance" in name:
        return "insurance"
    if "council" in name or "rate" in name:
        return "council"
    if "subscription" in name:
        return "subscription"
    if "child" in name or "education" in name:
        return "childcare"
    if "utilit" in name or "electric" in name or "water" in name or "gas" in name:
        return "utilities"
    return "other"
