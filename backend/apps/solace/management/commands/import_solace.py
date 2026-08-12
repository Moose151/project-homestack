"""Management command: import_solace (D14 — one-time native migration).

Imports from the standalone Project Solace SQLite database into the native Solace node.
The command is idempotent by natural keys and dry-runnable.

Usage
-----
    python manage.py import_solace --sqlite-db /home/instructor/Documents/new/project-solace/instance/solace.db --dry-run
    python manage.py import_solace --sqlite-db /home/instructor/Documents/new/project-solace/instance/solace.db
    python manage.py import_solace --sqlite-db /home/instructor/Documents/new/project-solace/instance/solace.db --verify
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
from apps.solace.models import (
    AccountBalanceSnapshot,
    Bill,
    BillOccurrence,
    BudgetBucket,
    CycleCloseout,
    FinanceCategory,
    Payday,
    PaydayChecklistItem,
    PaydayChecklistPreference,
    PlannedPurchase,
    SolaceSettings,
)
from apps.solace.services import (
    create_bill,
    create_bucket,
    create_checklist_item,
    create_payday,
    create_purchase,
    set_income_allocations,
)

# Where the standalone app keeps its database on this machine. Overridable with --sqlite-db,
# which is what any other install will need.
DEFAULT_DB = "/home/instructor/Documents/new/project-solace/instance/solace.db"


@dataclass
class LegacyData:
    categories: dict[int, str]
    category_rows: list[dict[str, Any]]
    bills: list[dict[str, Any]]
    occurrences: dict[int, list[dict[str, Any]]]
    purchases: list[dict[str, Any]]
    buckets: list[dict[str, Any]]
    incomes: list[dict[str, Any]]
    income_allocations: list[dict[str, Any]]
    checklist: list[dict[str, Any]]
    settings: list[dict[str, Any]]
    balances: list[dict[str, Any]]
    checklist_preferences: list[dict[str, Any]]
    closeouts: list[dict[str, Any]]


def _rows(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    return [dict(row) for row in conn.execute(f"select * from {table}")]


def _optional_rows(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    try:
        return _rows(conn, table)
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc).lower():
            return []
        raise


def _money(value) -> Decimal:
    return Decimal(str(value or "0")).quantize(Decimal("0.01"))


def _bool(value) -> bool:
    return bool(int(value or 0))


def _bucket_purpose(bucket_type: str | None) -> str:
    """Map the legacy app's free-text bucket_type onto BudgetBucket.Purpose.

    The legacy column was free text, so this matches on a contained word rather than equality
    ("Bills account", "bill", "BILLS" all land on bills) and falls back to Other rather than
    inventing a purpose it cannot infer.
    """
    text = (bucket_type or "").casefold()
    for token, purpose in (
        ("bill", BudgetBucket.Purpose.BILLS),
        ("saving", BudgetBucket.Purpose.SAVINGS),
        ("spend", BudgetBucket.Purpose.SPENDING),
        ("purchase", BudgetBucket.Purpose.PURCHASES),
    ):
        if token in text:
            return purpose
    return BudgetBucket.Purpose.OTHER


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


def _income_scope(value: str | None) -> str:
    return Payday.Scope.SHARED if (value or "").strip().lower() == "shared" else Payday.Scope.INDIVIDUAL


def _allocation_mode(value: str | None) -> str:
    mode = (value or "standard").strip().lower()
    return mode if mode in {"standard", "lump", "custom"} else "standard"


def _income_rrule(value: str | None) -> str:
    return {
        "weekly": "FREQ=WEEKLY",
        "fortnightly": "FREQ=WEEKLY;INTERVAL=2",
        "monthly": "FREQ=MONTHLY",
        "quarterly": "FREQ=MONTHLY;INTERVAL=3",
        "yearly": "FREQ=YEARLY",
    }.get((value or "").strip().lower(), "FREQ=WEEKLY;INTERVAL=2")


def _native_category(category_name: str) -> str:
    raw = (category_name or "").strip()
    known = {
        "mortgage": "mortgage",
        "mortgage / rent": "mortgage",
        "utilities": "utilities",
        "insurance": "insurance",
        "council": "council",
        "council / rates": "council",
        "debt": "debt",
        "subscriptions": "subscription",
        "subscription": "subscription",
        "childcare": "childcare",
        "childcare / education": "childcare",
        "travel": "travel",
        "christmas": "christmas",
        "home": "home",
        "other": "other",
    }
    return known.get(raw.casefold(), raw)


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
        category_rows = _rows(conn, "category")
        categories = {int(r["id"]): r["name"] for r in category_rows}
        occ: dict[int, list[dict[str, Any]]] = {}
        for row in _rows(conn, "bill_occurrence"):
            occ.setdefault(int(row["recurring_bill_id"]), []).append(row)
        return LegacyData(
            categories=categories,
            category_rows=category_rows,
            bills=_rows(conn, "recurring_bill"),
            occurrences=occ,
            purchases=_rows(conn, "planned_purchase"),
            buckets=_rows(conn, "bucket"),
            incomes=_rows(conn, "income_source"),
            income_allocations=_optional_rows(conn, "shared_income_allocation"),
            checklist=_rows(conn, "payday_checklist_item"),
            settings=_optional_rows(conn, "settings"),
            balances=_optional_rows(conn, "account_balance_snapshot"),
            checklist_preferences=_optional_rows(conn, "payday_checklist_preference"),
            closeouts=_optional_rows(conn, "cycle_closeout"),
        )
    except sqlite3.Error as exc:
        raise CommandError(f"Could not read legacy Solace database: {exc}")
    finally:
        conn.close()


class Command(BaseCommand):
    help = "Import standalone Project Solace SQLite data into the native Solace node. Dry-runnable."

    def add_arguments(self, parser):
        parser.add_argument("--sqlite-db", default=DEFAULT_DB, help="Path to legacy Project Solace SQLite DB.")
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument("--dry-run", action="store_true", help="Report what would be imported without writing.")
        mode.add_argument(
            "--verify",
            action="store_true",
            help="Read both databases and fail if imported legacy records do not match.",
        )

    def handle(self, *args, **options):
        household = get_active_household()
        if household is None:
            raise CommandError("No active household. Run migrations first.")

        data = _load_legacy(Path(options["sqlite_db"]))
        if options["verify"]:
            mismatches, checked = self._verify(data)
            if mismatches:
                details = "\n".join(f"  - {message}" for message in mismatches)
                raise CommandError(
                    f"Verification failed: {len(mismatches)} mismatch(es) "
                    f"across {checked} checks.\n{details}"
                )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Verification passed: {checked} source-to-native checks match."
                )
            )
            return

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
            "categories": 0,
            "bill_occurrences": 0,
            "bills_enriched": 0,
            "paydays": 0,
            "planned_purchases": 0,
            "buckets": 0,
            "bucket_rules_enriched": 0,
            "checklist_items": 0,
            "settings": 0,
            "balance_snapshots": 0,
            "checklist_preferences": 0,
            "cycle_closeouts": 0,
            "skipped_inactive": 0,
        }
        system_user = None
        household = get_active_household()

        for position, row in enumerate(data.category_rows, start=1):
            name = _native_category(row.get("name") or "")
            if not name:
                continue
            category_type = str(row.get("category_type") or "Both").strip().lower()
            if category_type not in {
                FinanceCategory.CategoryType.BILL,
                FinanceCategory.CategoryType.PURCHASE,
                FinanceCategory.CategoryType.BOTH,
            }:
                category_type = FinanceCategory.CategoryType.BOTH
            category = FinanceCategory.objects.filter(name__iexact=name).first()
            if category is None:
                FinanceCategory.objects.create(
                    household=household,
                    name=name,
                    category_type=category_type,
                    is_active=_bool(row.get("active")),
                    position=position * 10,
                )
                stats["categories"] += 1
            else:
                changed = False
                if category.category_type != category_type and category.category_type != "both":
                    category.category_type = "both"
                    changed = True
                active = _bool(row.get("active"))
                if category.is_active != active:
                    category.is_active = active
                    changed = True
                if changed:
                    category.save(update_fields=["category_type", "is_active", "updated_at"])

        if data.settings:
            row = data.settings[0]
            settings_obj = SolaceSettings.objects.first()
            created = settings_obj is None
            if settings_obj is None:
                settings_obj = SolaceSettings(household=household)
            settings_obj.currency_symbol = row.get("currency_symbol") or "$"
            settings_obj.budget_year = int(row["budget_year"]) if row.get("budget_year") else None
            settings_obj.cycle_anchor_date = _parse_date(row.get("first_payday"))
            settings_obj.default_buffer_amount = _money(row.get("default_buffer_amount"))
            handling = row.get("payday_bill_handling") or "new_cycle"
            settings_obj.payday_bill_handling = (
                handling if handling in {"new_cycle", "previous_cycle"} else "new_cycle"
            )
            settings_obj.show_help_tips = _bool(row.get("show_help_tips"))
            settings_obj.save()
            stats["settings"] += int(created)

        for row in data.balances:
            snapshot_date = _parse_date(row.get("snapshot_date"))
            if snapshot_date is None:
                continue
            _, created = AccountBalanceSnapshot.objects.update_or_create(
                household=household,
                snapshot_date=snapshot_date,
                defaults={
                    "balance": _money(row.get("balance")),
                    "notes": row.get("notes") or "",
                },
            )
            stats["balance_snapshots"] += int(created)

        for row in data.checklist_preferences:
            source_key = row.get("item_key") or ""
            if not source_key:
                continue
            _, created = PaydayChecklistPreference.objects.update_or_create(
                household=household,
                source_key=source_key,
                defaults={
                    "label": row.get("label") or source_key,
                    "is_hidden": _bool(row.get("hidden")),
                    "reason": row.get("reason") or "",
                },
            )
            stats["checklist_preferences"] += int(created)

        for row in data.closeouts:
            cycle_start = _parse_date(row.get("cycle_start"))
            cycle_end = _parse_date(row.get("cycle_end"))
            if cycle_start is None or cycle_end is None:
                continue
            closed = str(row.get("status") or "").lower() == "closed"
            _, created = CycleCloseout.objects.update_or_create(
                household=household,
                cycle_start=cycle_start,
                defaults={
                    "cycle_end": cycle_end,
                    "status": CycleCloseout.Status.CLOSED if closed else CycleCloseout.Status.OPEN,
                    "closed_at": _parse_dt(row.get("closed_at")) if closed else None,
                    "notes": row.get("notes") or "",
                },
            )
            stats["cycle_closeouts"] += int(created)

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
                "end_date": _parse_date(row.get("end_date")),
                "is_autopay": _bool(row.get("autopay")),
                "notes": row.get("notes") or "",
            }
            bill = Bill.objects.filter(name=row["name"]).first()
            if bill is None:
                bill = create_bill(
                    system_user,
                    name=row["name"],
                    category=_native_category(category) or "other",
                    due_at=due_at,
                    is_active=True,
                    include_in_set_aside=_bool(row.get("include_in_set_aside")),
                    is_paid=False,
                    paid_at=_latest_paid_at(occurrences),
                    **common,
                )
                stats["bills"] += 1
            else:
                changed_fields = []
                expected_end_date = _parse_date(row.get("end_date"))
                expected_autopay = _bool(row.get("autopay"))
                if bill.end_date != expected_end_date:
                    bill.end_date = expected_end_date
                    changed_fields.append("end_date")
                if bill.is_autopay != expected_autopay:
                    bill.is_autopay = expected_autopay
                    changed_fields.append("is_autopay")
                if changed_fields:
                    bill.save(update_fields=[*changed_fields, "updated_at"])
                    stats["bills_enriched"] += 1
            for occurrence in occurrences:
                occurrence_due = _parse_dt(occurrence.get("due_date"))
                if occurrence_due is None:
                    continue
                legacy_status = (occurrence.get("status") or "Upcoming").lower()
                occurrence_status = {
                    "paid": BillOccurrence.Status.PAID,
                    "skipped": BillOccurrence.Status.SKIPPED,
                }.get(legacy_status, BillOccurrence.Status.UPCOMING)
                _, created = BillOccurrence.objects.update_or_create(
                    bill=bill,
                    due_at=occurrence_due,
                    defaults={
                        "household": bill.household,
                        "amount": _money(occurrence.get("amount") or bill.amount),
                        "status": occurrence_status,
                        "paid_at": _parse_dt(occurrence.get("paid_date")),
                        "notes": occurrence.get("notes") or "",
                        "visibility": bill.visibility,
                        "sensitivity": bill.sensitivity,
                    },
                )
                stats["bill_occurrences"] += int(created)

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
                purpose=_bucket_purpose(row.get("bucket_type")),
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

        # Legacy bucket id -> imported bucket, so a shared income's split can be rebuilt.
        bucket_ids = {}
        for row in data.buckets:
            match = BudgetBucket.objects.filter(name=row["name"]).first()
            if match:
                bucket_ids[row["id"]] = match.id

        for row in data.incomes:
            if not _bool(row.get("active")):
                stats["skipped_inactive"] += 1
                continue
            title = f"{row.get('owner_name') or 'Household'}: {row.get('name') or 'Income'}"
            if Payday.objects.filter(title=title).exists():
                continue
            payday = create_payday(
                system_user,
                title=title,
                owner_name=row.get("owner_name") or "Household",
                income_scope=_income_scope(row.get("income_scope")),
                allocation_mode=_allocation_mode(row.get("allocation_mode")),
                lump_bucket_id=bucket_ids.get(row.get("lump_bucket_id")),
                expected_amount=_money(row.get("amount")),
                pay_at=_parse_dt(row.get("next_pay_date")),
                recurrence_rule=_income_rrule(row.get("frequency")),
                notes=row.get("notes") or f"Imported from legacy income source #{row['id']}.",
            )
            # A custom split is meaningless without the lines that define it, so they come across
            # with the income rather than in a separate pass.
            lines = [
                {
                    "bucket_id": bucket_ids[alloc["bucket_id"]],
                    "percentage": _money(alloc.get("percentage")),
                    "is_remainder": _bool(alloc.get("is_remainder")),
                }
                for alloc in sorted(
                    (a for a in data.income_allocations if a.get("income_source_id") == row["id"]),
                    key=lambda a: a.get("sort_order") or 0,
                )
                if alloc.get("bucket_id") in bucket_ids
            ]
            if lines:
                set_income_allocations(system_user, payday, lines)
                stats["income_allocations"] += len(lines)
            stats["paydays"] += 1

        for row in data.purchases:
            if PlannedPurchase.objects.filter(name=row["name"]).exists():
                continue
            create_purchase(
                system_user,
                name=row["name"],
                category=_native_category(
                    _category_name(data.categories, row.get("category_id"))
                ),
                target_amount=_money(row.get("target_amount")),
                saved_amount=_money(row.get("amount_saved")),
                target_date=_parse_dt(row.get("target_date")),
                status=_purchase_status(row.get("status")),
                priority=_priority(row.get("priority")),
                notes=row.get("notes") or "",
            )
            stats["planned_purchases"] += 1

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

    def _verify(self, data: LegacyData) -> tuple[list[str], int]:
        """Compare legacy source rows with their native natural-key counterparts.

        Native-only rows are allowed: Homestead mirrors and records created after cutover must
        not make verification fail. Every active/imported legacy row, however, must exist with
        the financially significant values preserved.
        """
        mismatches: list[str] = []
        checked = 0

        def mismatch(label: str, field: str, expected, actual) -> None:
            mismatches.append(f"{label}: {field} expected {expected!r}, found {actual!r}")

        def check(label: str, field: str, expected, actual) -> None:
            nonlocal checked
            checked += 1
            if expected != actual:
                mismatch(label, field, expected, actual)

        def local_date(value):
            if value is None:
                return None
            return timezone.localdate(value) if isinstance(value, datetime) else value

        for row in data.category_rows:
            name = _native_category(row.get("name") or "")
            if not name:
                continue
            label = f"category {name}"
            category = FinanceCategory.objects.filter(name__iexact=name).first()
            checked += 1
            if category is None:
                mismatches.append(f"{label}: missing")
                continue
            expected_type = str(row.get("category_type") or "Both").strip().lower()
            if expected_type not in {
                FinanceCategory.CategoryType.BILL,
                FinanceCategory.CategoryType.PURCHASE,
                FinanceCategory.CategoryType.BOTH,
            }:
                expected_type = FinanceCategory.CategoryType.BOTH
            checked += 1
            if (
                category.category_type != expected_type
                and category.category_type != FinanceCategory.CategoryType.BOTH
            ):
                mismatch(
                    label,
                    "category_type",
                    f"{expected_type} or both",
                    category.category_type,
                )
            check(label, "is_active", _bool(row.get("active")), category.is_active)

        for row in data.bills:
            if not _bool(row.get("active")):
                continue
            name = row.get("name") or ""
            label = f"bill {name}"
            bill = Bill.objects.filter(name=name).first()
            checked += 1
            if bill is None:
                mismatches.append(f"{label}: missing")
                continue
            occurrences = data.occurrences.get(int(row["id"]), [])
            check(label, "amount", _money(row.get("amount")), bill.amount)
            check(
                label,
                "category",
                _native_category(_category_name(data.categories, row.get("category_id"))) or "other",
                bill.category,
            )
            check(label, "provider", row.get("account_name") or "", bill.provider)
            check(label, "recurrence_rule", _rrule_from_legacy(row), bill.recurrence_rule)
            check(label, "end_date", _parse_date(row.get("end_date")), bill.end_date)
            check(label, "is_autopay", _bool(row.get("autopay")), bill.is_autopay)
            expected_due_dates = {
                local_date(parsed)
                for occurrence in occurrences
                if (parsed := _parse_dt(occurrence.get("due_date"))) is not None
            }
            start_date = local_date(_parse_dt(row.get("start_date")))
            if start_date is not None:
                expected_due_dates.add(start_date)
            if not expected_due_dates:
                expected_due_dates.add(None)
            checked += 1
            if local_date(bill.due_at) not in expected_due_dates:
                mismatch(
                    label,
                    "due_at",
                    f"one of {sorted(str(value) for value in expected_due_dates)}",
                    local_date(bill.due_at),
                )
            for occurrence in occurrences:
                due_at = _parse_dt(occurrence.get("due_date"))
                if due_at is None:
                    continue
                occurrence_label = f"{label} occurrence {local_date(due_at)}"
                native = BillOccurrence.objects.filter(bill=bill, due_at=due_at).first()
                checked += 1
                if native is None:
                    mismatches.append(f"{occurrence_label}: missing")
                    continue
                expected_status = {
                    "paid": BillOccurrence.Status.PAID,
                    "skipped": BillOccurrence.Status.SKIPPED,
                }.get(
                    (occurrence.get("status") or "Upcoming").lower(),
                    BillOccurrence.Status.UPCOMING,
                )
                check(
                    occurrence_label,
                    "amount",
                    _money(occurrence.get("amount") or bill.amount),
                    native.amount,
                )
                check(occurrence_label, "status", expected_status, native.status)
                check(
                    occurrence_label,
                    "paid_at",
                    local_date(_parse_dt(occurrence.get("paid_date"))),
                    local_date(native.paid_at),
                )

        for row in data.incomes:
            if not _bool(row.get("active")):
                continue
            title = f"{row.get('owner_name') or 'Household'}: {row.get('name') or 'Income'}"
            label = f"income {title}"
            payday = Payday.objects.filter(title=title).first()
            checked += 1
            if payday is None:
                mismatches.append(f"{label}: missing")
                continue
            check(label, "expected_amount", _money(row.get("amount")), payday.expected_amount)
            check(
                label,
                "pay_at",
                local_date(_parse_dt(row.get("next_pay_date"))),
                local_date(payday.pay_at),
            )
            check(
                label,
                "recurrence_rule",
                _income_rrule(row.get("frequency")),
                payday.recurrence_rule,
            )

        for row in data.purchases:
            name = row.get("name") or ""
            label = f"purchase {name}"
            purchase = PlannedPurchase.objects.filter(name=name).first()
            checked += 1
            if purchase is None:
                mismatches.append(f"{label}: missing")
                continue
            check(label, "target_amount", _money(row.get("target_amount")), purchase.target_amount)
            check(label, "saved_amount", _money(row.get("amount_saved")), purchase.saved_amount)
            check(
                label,
                "target_date",
                local_date(_parse_dt(row.get("target_date"))),
                local_date(purchase.target_date),
            )
            check(label, "status", _purchase_status(row.get("status")), purchase.status)
            check(label, "priority", _priority(row.get("priority")), purchase.priority)

        for row in data.buckets:
            if not _bool(row.get("active")):
                continue
            name = row.get("name") or ""
            label = f"bucket {name}"
            bucket = BudgetBucket.objects.filter(name=name).first()
            checked += 1
            if bucket is None:
                mismatches.append(f"{label}: missing")
                continue
            fixed = row.get("fixed_amount")
            check(
                label,
                "allocation_method",
                (
                    BudgetBucket.AllocationMethod.FIXED
                    if fixed not in (None, "")
                    else BudgetBucket.AllocationMethod.PERCENTAGE
                ),
                bucket.allocation_method,
            )
            check(
                label,
                "allocation_value",
                _money(fixed if fixed not in (None, "") else row.get("percentage")),
                bucket.allocation_value,
            )
            check(
                label,
                "rounding_increment",
                _money(row.get("rounding_increment") or 1),
                bucket.rounding_increment,
            )
            check(
                label,
                "cap_to_remaining",
                _bool(row.get("cap_to_remaining")),
                bucket.cap_to_remaining,
            )
            check(label, "position", int(row.get("sort_order") or 0), bucket.position)

        if data.settings:
            row = data.settings[0]
            settings_obj = SolaceSettings.objects.first()
            checked += 1
            if settings_obj is None:
                mismatches.append("settings: missing")
            else:
                check(
                    "settings",
                    "currency_symbol",
                    row.get("currency_symbol") or "$",
                    settings_obj.currency_symbol,
                )
                check(
                    "settings",
                    "budget_year",
                    int(row["budget_year"]) if row.get("budget_year") else None,
                    settings_obj.budget_year,
                )
                check(
                    "settings",
                    "cycle_anchor_date",
                    _parse_date(row.get("first_payday")),
                    settings_obj.cycle_anchor_date,
                )
                check(
                    "settings",
                    "default_buffer_amount",
                    _money(row.get("default_buffer_amount")),
                    settings_obj.default_buffer_amount,
                )
                expected_handling = row.get("payday_bill_handling") or "new_cycle"
                if expected_handling not in {"new_cycle", "previous_cycle"}:
                    expected_handling = "new_cycle"
                check(
                    "settings",
                    "payday_bill_handling",
                    expected_handling,
                    settings_obj.payday_bill_handling,
                )
                check(
                    "settings",
                    "show_help_tips",
                    _bool(row.get("show_help_tips")),
                    settings_obj.show_help_tips,
                )

        for row in data.balances:
            snapshot_date = _parse_date(row.get("snapshot_date"))
            if snapshot_date is None:
                continue
            label = f"balance {snapshot_date}"
            native = AccountBalanceSnapshot.objects.filter(snapshot_date=snapshot_date).first()
            checked += 1
            if native is None:
                mismatches.append(f"{label}: missing")
                continue
            check(label, "balance", _money(row.get("balance")), native.balance)

        for row in data.checklist_preferences:
            source_key = row.get("item_key") or ""
            if not source_key:
                continue
            label = f"checklist preference {source_key}"
            native = PaydayChecklistPreference.objects.filter(source_key=source_key).first()
            checked += 1
            if native is None:
                mismatches.append(f"{label}: missing")
                continue
            check(label, "is_hidden", _bool(row.get("hidden")), native.is_hidden)

        for row in data.closeouts:
            cycle_start = _parse_date(row.get("cycle_start"))
            if cycle_start is None:
                continue
            label = f"closeout {cycle_start}"
            native = CycleCloseout.objects.filter(cycle_start=cycle_start).first()
            checked += 1
            if native is None:
                mismatches.append(f"{label}: missing")
                continue
            expected_status = (
                CycleCloseout.Status.CLOSED
                if str(row.get("status") or "").lower() == "closed"
                else CycleCloseout.Status.OPEN
            )
            check(label, "cycle_end", _parse_date(row.get("cycle_end")), native.cycle_end)
            check(label, "status", expected_status, native.status)

        latest_cycle = max((row.get("cycle_start") or "" for row in data.checklist), default="")
        for row in data.checklist:
            if row.get("cycle_start") != latest_cycle:
                continue
            title = row.get("label") or row.get("item_key") or "Checklist item"
            position = int(row.get("sort_order") or 0)
            label = f"checklist item {title}"
            native = PaydayChecklistItem.objects.filter(title=title, position=position).first()
            checked += 1
            if native is None:
                mismatches.append(f"{label}: missing")
                continue
            check(label, "cycle_start", _parse_date(latest_cycle), native.cycle_start)
            check(label, "amount_hint", _money(row.get("amount")), native.amount_hint)
            check(label, "is_complete", _bool(row.get("completed")), native.is_complete)

        return mismatches, checked
