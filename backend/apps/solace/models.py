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
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.OTHER)
    provider = models.CharField(max_length=200, blank=True, default="")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    due_at = models.DateTimeField(null=True, blank=True)
    is_all_day = models.BooleanField(default=True)
    recurrence_rule = models.CharField(max_length=512, blank=True, default="")
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
        return bool(self.due_at and not self.is_paid and self.due_at < timezone.now())

    def get_calendar_data(self) -> dict | None:
        if not self.due_at or self.is_paid:
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


class Payday(CalendarSyncMixin, HouseholdBaseModel):
    title = models.CharField(max_length=200, default="Payday")
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

    name = models.CharField(max_length=200)
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


class Subscription(CalendarSyncMixin, HouseholdBaseModel):
    class BillingCycle(models.TextChoices):
        WEEKLY = "weekly", "Weekly"
        FORTNIGHTLY = "fortnightly", "Fortnightly"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        YEARLY = "yearly", "Yearly"
        OTHER = "other", "Other"

    name = models.CharField(max_length=200)
    provider = models.CharField(max_length=200, blank=True, default="")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    billing_cycle = models.CharField(max_length=20, choices=BillingCycle.choices, default=BillingCycle.MONTHLY)
    next_renewal_at = models.DateTimeField(null=True, blank=True)
    is_all_day = models.BooleanField(default=True)
    recurrence_rule = models.CharField(max_length=512, blank=True, default="")
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default="")
    calendar_event_id = models.PositiveBigIntegerField(null=True, blank=True)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.SENSITIVE)
    sensitivity = models.CharField(max_length=20, choices=Sensitivity.choices, default=Sensitivity.FINANCIAL)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["next_renewal_at", "name"]

    def __str__(self) -> str:
        return self.name

    def get_calendar_data(self) -> dict | None:
        if not self.next_renewal_at or not self.is_active:
            return None
        return {
            "title": f"Subscription: {self.name}",
            "start_at": self.next_renewal_at,
            "is_all_day": self.is_all_day,
            "description": self.notes,
            "recurrence_rule": self.recurrence_rule,
            "visibility": self.visibility,
            "sensitivity": self.sensitivity,
            "colour": "#426e9b",
        }

    def get_calendar_node_key(self) -> str:
        return "solace"


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
