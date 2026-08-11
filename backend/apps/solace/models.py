"""solace models — native household finance node (Node Spec 22).

Solace is sensitive throughout: rows default to visibility=sensitive and
sensitivity=financial, routes require password re-auth, and dated records sync to Calendar
through the scheduling helper only (D7/D8).
"""
from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.core.models import AllObjectsManager, HouseholdBaseModel, HouseholdManager
from apps.scheduling.mixins import CalendarSyncMixin


class Visibility(models.TextChoices):
    PRIVATE = "private", "Private"
    HOUSEHOLD = "household", "Household"
    ROLE_RESTRICTED = "role_restricted", "Role Restricted"
    SENSITIVE = "sensitive", "Sensitive"


class Sensitivity(models.TextChoices):
    NORMAL = "normal", "Normal"
    FINANCIAL = "financial", "Financial"
    HEALTH = "health", "Health"
    DOCUMENT = "document", "Document"
    PRIVATE = "private", "Private"


class Bill(CalendarSyncMixin, HouseholdBaseModel):
    class Category(models.TextChoices):
        MORTGAGE = "mortgage", "Mortgage / rent"
        UTILITIES = "utilities", "Utilities"
        INSURANCE = "insurance", "Insurance"
        COUNCIL = "council", "Council / rates"
        DEBT = "debt", "Debt"
        SUBSCRIPTION = "subscription", "Subscription"
        CHILDCARE = "childcare", "Childcare / education"
        OTHER = "other", "Other"

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100, default=Category.OTHER)
    provider = models.CharField(max_length=200, blank=True, default="")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    due_at = models.DateTimeField(null=True, blank=True)
    is_all_day = models.BooleanField(default=True)
    recurrence_rule = models.CharField(max_length=512, blank=True, default="")
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_autopay = models.BooleanField(default=False)
    include_in_set_aside = models.BooleanField(default=True)
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    source_node = models.CharField(max_length=50, blank=True, default="")
    source_record_type = models.CharField(max_length=100, blank=True, default="")
    source_record_id = models.PositiveBigIntegerField(null=True, blank=True)
    calendar_event_id = models.PositiveBigIntegerField(null=True, blank=True)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.SENSITIVE)
    sensitivity = models.CharField(max_length=20, choices=Sensitivity.choices, default=Sensitivity.FINANCIAL)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["due_at", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["household", "source_node", "source_record_type", "source_record_id"],
                condition=(
                    models.Q(deleted_at__isnull=True)
                    & ~models.Q(source_node="")
                    & ~models.Q(source_record_type="")
                    & models.Q(source_record_id__isnull=False)
                ),
                name="unique_active_solace_source_bill",
            )
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def is_overdue(self) -> bool:
        occurrence = self.occurrences.filter(status=BillOccurrence.Status.UPCOMING).first()
        if occurrence:
            return occurrence.is_overdue
        return bool(
            self.due_at
            and not self.recurrence_rule
            and not self.is_paid
            and self.due_at < timezone.now()
        )

    def get_calendar_data(self) -> dict | None:
        if not self.due_at or not self.is_active or (self.is_paid and not self.recurrence_rule):
            return None
        return {
            "title": f"Bill: {self.name}",
            "start_at": self.due_at,
            "is_all_day": self.is_all_day,
            "description": self.notes,
            "recurrence_rule": self.recurrence_rule,
            "visibility": self.visibility,
            "sensitivity": self.sensitivity,
            "colour": "#8f4e38",
        }

    def get_calendar_node_key(self) -> str:
        return "solace"


class BillOccurrence(HouseholdBaseModel):
    class Status(models.TextChoices):
        UPCOMING = "upcoming", "Upcoming"
        PAID = "paid", "Paid"
        SKIPPED = "skipped", "Skipped"

    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="occurrences")
    due_at = models.DateTimeField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPCOMING)
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.SENSITIVE)
    sensitivity = models.CharField(max_length=20, choices=Sensitivity.choices, default=Sensitivity.FINANCIAL)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["due_at", "bill__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["household", "bill", "due_at"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_solace_bill_occurrence",
            )
        ]

    def __str__(self) -> str:
        return f"{self.bill.name} — {self.due_at:%Y-%m-%d}"

    @property
    def is_overdue(self) -> bool:
        return self.status == self.Status.UPCOMING and self.due_at < timezone.now()


class Payday(CalendarSyncMixin, HouseholdBaseModel):
    class Scope(models.TextChoices):
        """Whose income this is.

        Shared income belongs to the household rather than a person: it is left out of the
        per-person contribution breakdown and applied to buckets after the personal splits.
        """

        INDIVIDUAL = "individual", "One person's income"
        SHARED = "shared", "Shared household income"

    class AllocationMode(models.TextChoices):
        """How this income reaches the buckets. Only meaningful for shared income."""

        STANDARD = "standard", "Through the usual bucket rules"
        LUMP = "lump", "All of it into one bucket"
        CUSTOM = "custom", "Split across chosen buckets"

    title = models.CharField(max_length=200, default="Payday")
    # Free text rather than a Person link: an income can belong to someone who has no profile,
    # and the standalone app this replaces groups contributions by name.
    owner_name = models.CharField(max_length=120, blank=True, default="Household")
    income_scope = models.CharField(max_length=20, choices=Scope.choices, default=Scope.INDIVIDUAL)
    allocation_mode = models.CharField(
        max_length=20, choices=AllocationMode.choices, default=AllocationMode.STANDARD
    )
    lump_bucket = models.ForeignKey(
        "solace.BudgetBucket", on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    expected_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    pay_at = models.DateTimeField(null=True, blank=True)
    is_all_day = models.BooleanField(default=True)
    recurrence_rule = models.CharField(max_length=512, blank=True, default="")
    received_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default="")
    calendar_event_id = models.PositiveBigIntegerField(null=True, blank=True)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.SENSITIVE)
    sensitivity = models.CharField(max_length=20, choices=Sensitivity.choices, default=Sensitivity.FINANCIAL)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["pay_at", "title"]

    def __str__(self) -> str:
        return self.title

    def get_calendar_data(self) -> dict | None:
        if not self.pay_at or not self.is_active:
            return None
        return {
            "title": self.title,
            "start_at": self.pay_at,
            "is_all_day": self.is_all_day,
            "description": self.notes,
            "recurrence_rule": self.recurrence_rule,
            "visibility": self.visibility,
            "sensitivity": self.sensitivity,
            "colour": "#287c68",
        }

    def get_calendar_node_key(self) -> str:
        return "solace"


class IncomeAllocation(HouseholdBaseModel):
    """One line of a shared income's custom split: send this share to this bucket.

    Exactly one line per income may be the remainder, which receives whatever is left after the
    percentages are applied — the same idea as a bucket capping itself to the remaining pay.
    """

    payday = models.ForeignKey(Payday, on_delete=models.CASCADE, related_name="allocations")
    bucket = models.ForeignKey("solace.BudgetBucket", on_delete=models.CASCADE, related_name="+")
    percentage = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    is_remainder = models.BooleanField(default=False)
    position = models.PositiveSmallIntegerField(default=0)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.SENSITIVE)
    sensitivity = models.CharField(max_length=20, choices=Sensitivity.choices, default=Sensitivity.FINANCIAL)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["position", "id"]
        verbose_name = "income allocation"

    def __str__(self) -> str:
        return f"{self.payday.title} → {self.bucket.name}"


class PlannedPurchase(CalendarSyncMixin, HouseholdBaseModel):
    class Status(models.TextChoices):
        IDEA = "idea", "Idea"
        SAVING = "saving", "Saving"
        READY = "ready", "Ready"
        BOUGHT = "bought", "Bought"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100, blank=True, default="")
    target_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    saved_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    target_date = models.DateTimeField(null=True, blank=True)
    is_all_day = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SAVING)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    notes = models.TextField(blank=True, default="")
    calendar_event_id = models.PositiveBigIntegerField(null=True, blank=True)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.SENSITIVE)
    sensitivity = models.CharField(max_length=20, choices=Sensitivity.choices, default=Sensitivity.FINANCIAL)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["target_date", "-updated_at"]

    def __str__(self) -> str:
        return self.name

    @property
    def remaining_amount(self) -> Decimal:
        remaining = Decimal(self.target_amount) - Decimal(self.saved_amount)
        return remaining if remaining > 0 else Decimal("0.00")

    @property
    def progress_percent(self) -> int:
        target = Decimal(self.target_amount)
        saved = Decimal(self.saved_amount)
        if target <= 0:
            return 0
        return min(100, int((saved / target) * 100))

    @property
    def is_open(self) -> bool:
        return self.status not in (self.Status.BOUGHT, self.Status.CANCELLED)

    def get_calendar_data(self) -> dict | None:
        if not self.target_date or not self.is_open:
            return None
        return {
            "title": f"Planned purchase: {self.name}",
            "start_at": self.target_date,
            "is_all_day": self.is_all_day,
            "description": self.notes,
            "visibility": self.visibility,
            "sensitivity": self.sensitivity,
            "colour": "#7662a8",
        }

    def get_calendar_node_key(self) -> str:
        return "solace"


class BudgetBucket(HouseholdBaseModel):
    class AllocationMethod(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage of pay"
        FIXED = "fixed", "Fixed household amount"

    class Purpose(models.TextChoices):
        """What the bucket is for, which is how a household reads its list of them."""

        BILLS = "bills", "Bills"
        SAVINGS = "savings", "Savings"
        SPENDING = "spending", "Spending"
        PURCHASES = "purchases", "Planned purchases"
        OTHER = "other", "Other"

    name = models.CharField(max_length=200)
    purpose = models.CharField(max_length=20, choices=Purpose.choices, default=Purpose.OTHER)
    category = models.CharField(max_length=100, blank=True, default="")
    target_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    current_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    allocation_method = models.CharField(
        max_length=20,
        choices=AllocationMethod.choices,
        default=AllocationMethod.PERCENTAGE,
    )
    allocation_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    rounding_increment = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("1.00"))
    cap_to_remaining = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    position = models.PositiveSmallIntegerField(default=0)
    notes = models.TextField(blank=True, default="")
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.SENSITIVE)
    sensitivity = models.CharField(max_length=20, choices=Sensitivity.choices, default=Sensitivity.FINANCIAL)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["position", "name"]

    def __str__(self) -> str:
        return self.name

    @property
    def remaining_amount(self) -> Decimal:
        remaining = Decimal(self.target_amount) - Decimal(self.current_amount)
        return remaining if remaining > 0 else Decimal("0.00")

    @property
    def progress_percent(self) -> int:
        target = Decimal(self.target_amount)
        current = Decimal(self.current_amount)
        if target <= 0:
            return 0
        return min(100, int((current / target) * 100))


class BucketEntry(HouseholdBaseModel):
    """One movement of money into or out of a bucket.

    A bucket balance used to be a number you overwrote, so "what is in the car fund" had no
    history and no explanation. Every change now goes through an entry — the balance on
    `BudgetBucket.current_amount` stays as the running total the pay planner already reads, and
    these rows are the audit of how it got there.
    """

    class Kind(models.TextChoices):
        DEPOSIT = "deposit", "Money in"
        WITHDRAWAL = "withdrawal", "Money out"
        ADJUSTMENT = "adjustment", "Correction"

    bucket = models.ForeignKey(BudgetBucket, on_delete=models.CASCADE, related_name="entries")
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.DEPOSIT)
    # Always positive; `kind` carries the direction so a total never depends on a sign convention.
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    occurred_at = models.DateTimeField()
    note = models.CharField(max_length=255, blank=True, default="")
    # The balance immediately after this entry, so history reads correctly without replaying it.
    balance_after = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.SENSITIVE)
    sensitivity = models.CharField(max_length=20, choices=Sensitivity.choices, default=Sensitivity.FINANCIAL)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["-occurred_at", "-id"]
        verbose_name = "bucket entry"
        verbose_name_plural = "bucket entries"

    def __str__(self) -> str:
        return f"{self.bucket.name} {self.kind} {self.amount}"

    @property
    def signed_amount(self) -> Decimal:
        amount = Decimal(self.amount)
        return -amount if self.kind == self.Kind.WITHDRAWAL else amount


class PaydayChecklistItem(HouseholdBaseModel):
    title = models.CharField(max_length=200)
    cycle_start = models.DateField(null=True, blank=True)
    source_key = models.CharField(max_length=120, blank=True, default="")
    bucket = models.ForeignKey(
        BudgetBucket, on_delete=models.SET_NULL, null=True, blank=True, related_name="checklist_items"
    )
    bill = models.ForeignKey(
        Bill, on_delete=models.SET_NULL, null=True, blank=True, related_name="checklist_items"
    )
    amount_hint = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    position = models.PositiveSmallIntegerField(default=0)
    is_complete = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.SENSITIVE)
    sensitivity = models.CharField(max_length=20, choices=Sensitivity.choices, default=Sensitivity.FINANCIAL)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["-cycle_start", "is_complete", "position", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["household", "cycle_start", "source_key"],
                condition=(
                    models.Q(deleted_at__isnull=True)
                    & models.Q(cycle_start__isnull=False)
                    & ~models.Q(source_key="")
                ),
                name="unique_active_solace_cycle_checklist_source",
            )
        ]

    def __str__(self) -> str:
        return self.title


class SolaceSettings(HouseholdBaseModel):
    class PaydayBillHandling(models.TextChoices):
        NEW_CYCLE = "new_cycle", "New pay cycle"
        PREVIOUS_CYCLE = "previous_cycle", "Previous pay cycle"

    currency_symbol = models.CharField(max_length=8, default="$")
    budget_year = models.PositiveSmallIntegerField(null=True, blank=True)
    cycle_anchor_date = models.DateField(null=True, blank=True)
    default_buffer_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    payday_bill_handling = models.CharField(
        max_length=20,
        choices=PaydayBillHandling.choices,
        default=PaydayBillHandling.NEW_CYCLE,
    )
    show_help_tips = models.BooleanField(default=True)
    dashboard_reminders = models.BooleanField(default=True)
    due_soon_days = models.PositiveSmallIntegerField(default=3)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name_plural = "Solace settings"
        constraints = [
            models.UniqueConstraint(
                fields=["household"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_solace_settings",
            )
        ]

    def __str__(self) -> str:
        return f"Solace settings — {self.household}"


class FinanceCategory(HouseholdBaseModel):
    class CategoryType(models.TextChoices):
        BILL = "bill", "Bill"
        PURCHASE = "purchase", "Purchase"
        BOTH = "both", "Both"

    name = models.CharField(max_length=100)
    category_type = models.CharField(
        max_length=20,
        choices=CategoryType.choices,
        default=CategoryType.BOTH,
    )
    is_active = models.BooleanField(default=True)
    position = models.PositiveSmallIntegerField(default=0)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.SENSITIVE)
    sensitivity = models.CharField(max_length=20, choices=Sensitivity.choices, default=Sensitivity.FINANCIAL)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["position", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["household", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_solace_category_name",
            )
        ]

    def __str__(self) -> str:
        return self.name


class AccountBalanceSnapshot(HouseholdBaseModel):
    snapshot_date = models.DateField(default=timezone.localdate)
    balance = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True, default="")
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.SENSITIVE)
    sensitivity = models.CharField(max_length=20, choices=Sensitivity.choices, default=Sensitivity.FINANCIAL)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["-snapshot_date", "-id"]

    def __str__(self) -> str:
        return f"{self.snapshot_date}: {self.balance}"


class PaydayChecklistPreference(HouseholdBaseModel):
    source_key = models.CharField(max_length=120)
    label = models.CharField(max_length=200)
    is_hidden = models.BooleanField(default=False)
    reason = models.CharField(max_length=200, blank=True, default="")
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.SENSITIVE)
    sensitivity = models.CharField(max_length=20, choices=Sensitivity.choices, default=Sensitivity.FINANCIAL)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["label"]
        constraints = [
            models.UniqueConstraint(
                fields=["household", "source_key"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_solace_checklist_preference",
            )
        ]

    def __str__(self) -> str:
        return self.label


class CycleCloseout(HouseholdBaseModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    cycle_start = models.DateField()
    cycle_end = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    closed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.SENSITIVE)
    sensitivity = models.CharField(max_length=20, choices=Sensitivity.choices, default=Sensitivity.FINANCIAL)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["-cycle_start"]
        constraints = [
            models.UniqueConstraint(
                fields=["household", "cycle_start"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_solace_cycle_closeout",
            )
        ]

    def __str__(self) -> str:
        return f"{self.cycle_start} — {self.status}"
