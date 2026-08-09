"""homestead models — the household's home/property hub (Node Spec 25).

V1 slice: the property record (with practical emergency info), recurring/one-off maintenance,
appliances + warranties, a service-provider directory, and a lightweight improvements list.

Design intent (owner, 2026-07-21): Homestead is an *aggregating* home hub. The financial node
(Solace) owns household cash-flow while Homestead owns home-specific policies/accounts and room
planning estimates. Cross-node data moves through events, never model imports (D4), and
`Improvement.project_ref` remains the hook to a future full Project.

All models inherit HouseholdBaseModel (household scoping, audit, soft-delete). Maintenance and
improvement dates mirror to the shared calendar via the scheduling helper only (D7); recurring
maintenance carries an RRULE (D8). Nothing household-specific is hardcoded (D15).
"""
from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import AllObjectsManager, HouseholdBaseModel, HouseholdManager
from apps.scheduling.mixins import CalendarSyncMixin


class Visibility(models.TextChoices):
    PRIVATE = "private", "Private"
    HOUSEHOLD = "household", "Household"
    ROLE_RESTRICTED = "role_restricted", "Role Restricted"
    SENSITIVE = "sensitive", "Sensitive"


class Property(HouseholdBaseModel):
    """The home itself. Usually one row, but multiple are allowed (e.g. a second property)."""

    class PropertyType(models.TextChoices):
        HOUSE = "house", "House"
        FLAT = "flat", "Flat / apartment"
        BUNGALOW = "bungalow", "Bungalow"
        MAISONETTE = "maisonette", "Maisonette"
        OTHER = "other", "Other"

    class Tenure(models.TextChoices):
        FREEHOLD = "freehold", "Freehold"
        LEASEHOLD = "leasehold", "Leasehold"
        SHARE_OF_FREEHOLD = "share_of_freehold", "Share of freehold"
        RENTED = "rented", "Rented"
        OTHER = "other", "Other"
        UNKNOWN = "unknown", "Unknown"

    name = models.CharField(max_length=160, default="Home")
    address = models.TextField(blank=True, default="")
    property_type = models.CharField(
        max_length=20, choices=PropertyType.choices, default=PropertyType.HOUSE
    )
    tenure = models.CharField(max_length=20, choices=Tenure.choices, default=Tenure.UNKNOWN)
    purchase_date = models.DateField(null=True, blank=True)
    move_in_date = models.DateField(null=True, blank=True)
    year_built = models.CharField(max_length=20, blank=True, default="")
    is_primary = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default="")

    # Practical "where is it?" info — kiosk-safe, household-visible by default.
    water_shutoff = models.CharField(max_length=255, blank=True, default="")
    gas_shutoff = models.CharField(max_length=255, blank=True, default="")
    electricity_consumer_unit = models.CharField(max_length=255, blank=True, default="")
    boiler_location = models.CharField(max_length=255, blank=True, default="")

    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "property"
        verbose_name_plural = "properties"
        ordering = ["-is_primary", "name"]

    def __str__(self) -> str:
        return self.name


class ServiceProvider(HouseholdBaseModel):
    """A tradesperson / contractor the household uses (plumber, electrician, …)."""

    class Trade(models.TextChoices):
        PLUMBER = "plumber", "Plumber"
        ELECTRICIAN = "electrician", "Electrician"
        GAS_ENGINEER = "gas_engineer", "Gas / heating engineer"
        BUILDER = "builder", "Builder"
        GARDENER = "gardener", "Gardener"
        CLEANER = "cleaner", "Cleaner"
        ROOFER = "roofer", "Roofer"
        PEST_CONTROL = "pest_control", "Pest control"
        HANDYMAN = "handyman", "Handyman"
        OTHER = "other", "Other"

    name = models.CharField(max_length=200)
    trade = models.CharField(max_length=20, choices=Trade.choices, default=Trade.OTHER)
    company = models.CharField(max_length=200, blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    email = models.CharField(max_length=254, blank=True, default="")
    website = models.CharField(max_length=255, blank=True, default="")
    last_used_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "service provider"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Appliance(HouseholdBaseModel):
    """An appliance or home system, with warranty + reference details (Assets home scope)."""

    class Category(models.TextChoices):
        APPLIANCE = "appliance", "Appliance"
        HEATING = "heating", "Heating / boiler"
        KITCHEN = "kitchen", "Kitchen"
        LAUNDRY = "laundry", "Laundry"
        ELECTRICAL = "electrical", "Electrical"
        PLUMBING = "plumbing", "Plumbing"
        SECURITY = "security", "Security"
        OUTDOOR = "outdoor", "Outdoor / garden"
        OTHER = "other", "Other"

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.APPLIANCE)
    brand = models.CharField(max_length=160, blank=True, default="")
    model_number = models.CharField(max_length=160, blank=True, default="")
    serial_number = models.CharField(max_length=160, blank=True, default="")
    room = models.CharField(max_length=120, blank=True, default="")
    purchase_date = models.DateField(null=True, blank=True)
    warranty_expires_at = models.DateField(null=True, blank=True)
    warranty_provider = models.CharField(max_length=200, blank=True, default="")
    manual_url = models.CharField(max_length=500, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "appliance"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class MaintenanceTask(CalendarSyncMixin, HouseholdBaseModel):
    """Recurring or one-off home upkeep / renewal (the Pets-treatment pattern, D7/D8).

    `next_due_at` is the source of truth for the reminder and drives the calendar event.
    Marking a task done advances `next_due_at` to the next RRULE occurrence, clearing the
    reminder when it is non-recurring.
    """

    class Category(models.TextChoices):
        HEATING = "heating", "Heating"
        PLUMBING = "plumbing", "Plumbing"
        ELECTRICAL = "electrical", "Electrical"
        SAFETY = "safety", "Safety"
        GARDEN = "garden", "Garden / outdoor"
        EXTERIOR = "exterior", "Exterior"
        CLEANING = "cleaning", "Cleaning"
        APPLIANCE = "appliance", "Appliance"
        RENEWAL = "renewal", "Renewal / admin"
        GENERAL = "general", "General"

    appliance = models.ForeignKey(
        Appliance, on_delete=models.SET_NULL, null=True, blank=True, related_name="maintenance_tasks"
    )
    provider = models.ForeignKey(
        ServiceProvider, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    assigned_to_person = models.ForeignKey(
        "people.Person", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.GENERAL)
    next_due_at = models.DateTimeField(null=True, blank=True)
    is_all_day = models.BooleanField(default=True)
    recurrence_rule = models.CharField(max_length=512, blank=True, default="")
    last_done_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    solace_bill_ref = models.PositiveBigIntegerField(null=True, blank=True, editable=False)
    calendar_event_id = models.PositiveBigIntegerField(null=True, blank=True)
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "maintenance task"
        ordering = ["next_due_at", "-updated_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def is_overdue(self) -> bool:
        from django.utils import timezone
        return bool(self.next_due_at and self.next_due_at < timezone.now())

    # --- CalendarSyncMixin contract ---

    def get_calendar_data(self) -> dict | None:
        if not self.next_due_at:
            return None
        return {
            "title": self.title,
            "start_at": self.next_due_at,
            "is_all_day": self.is_all_day,
            "description": self.notes,
            "recurrence_rule": self.recurrence_rule,
            "visibility": self.visibility,
        }

    def get_calendar_node_key(self) -> str:
        return "homestead"


class Improvement(CalendarSyncMixin, HouseholdBaseModel):
    """A home improvement / project (renovation, room makeover, garden build).

    Lightweight in V1. `project_ref` is a dormant forward-hook: once the dedicated Projects node
    exists, an improvement can link to a full Project (Homestead deep-links to it, D4).
    """

    class Status(models.TextChoices):
        IDEA = "idea", "Idea"
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In progress"
        ON_HOLD = "on_hold", "On hold"
        DONE = "done", "Done"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    assigned_to_person = models.ForeignKey(
        "people.Person", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IDEA)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    room = models.CharField(max_length=120, blank=True, default="")
    target_date = models.DateTimeField(null=True, blank=True)
    is_all_day = models.BooleanField(default=True)
    project_ref = models.PositiveBigIntegerField(null=True, blank=True)  # future Projects node link
    notes = models.TextField(blank=True, default="")
    calendar_event_id = models.PositiveBigIntegerField(null=True, blank=True)
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "improvement"
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def is_open(self) -> bool:
        return self.status not in (self.Status.DONE, self.Status.CANCELLED)

    # --- CalendarSyncMixin contract ---

    def get_calendar_data(self) -> dict | None:
        # Only surface open, dated improvements on the calendar.
        if not self.target_date or not self.is_open:
            return None
        return {
            "title": f"{self.title} (improvement)",
            "start_at": self.target_date,
            "is_all_day": self.is_all_day,
            "description": self.description,
            "visibility": self.visibility,
        }

    def get_calendar_node_key(self) -> str:
        return "homestead"


class RoomArea(HouseholdBaseModel):
    """A stable room/area destination, ready for a future clickable floor plan."""

    class AreaType(models.TextChoices):
        INTERIOR = "interior", "Interior room"
        OUTDOOR = "outdoor", "Outdoor area"
        UTILITY = "utility", "Utility / service area"
        STORAGE = "storage", "Storage"
        OTHER = "other", "Other"

    name = models.CharField(max_length=160)
    area_type = models.CharField(
        max_length=20, choices=AreaType.choices, default=AreaType.INTERIOR
    )
    description = models.TextField(blank=True, default="")
    icon = models.CharField(max_length=50, blank=True, default="")
    colour = models.CharField(max_length=20, blank=True, default="#B0563C")
    display_order = models.PositiveSmallIntegerField(default=0)
    # Flexible coordinates/shape metadata for the future floor-plan renderer. The room ID and
    # detail route stay stable when that visual layer arrives.
    floorplan_data = models.JSONField(default=dict, blank=True)
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "room or area"
        ordering = ["display_order", "name", "id"]

    def __str__(self) -> str:
        return self.name


class RoomPlanItem(HouseholdBaseModel):
    """One wanted purchase, maintenance job, renovation or upgrade for a room."""

    class ItemType(models.TextChoices):
        PURCHASE = "purchase", "Purchase"
        MAINTENANCE = "maintenance", "Maintenance"
        RENOVATION = "renovation", "Renovation"
        UPGRADE = "upgrade", "Upgrade"

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        ARCHIVED = "archived", "Archived"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    room = models.ForeignKey(RoomArea, on_delete=models.PROTECT, related_name="plan_items")
    assigned_to_person = models.ForeignKey(
        "people.Person", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    title = models.CharField(max_length=255)
    item_type = models.CharField(
        max_length=20, choices=ItemType.choices, default=ItemType.PURCHASE
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    description = models.TextField(blank=True, default="")
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("1.00"),
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    estimated_unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    # Actual cost is the total paid, not a per-unit amount.
    actual_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    notes = models.TextField(blank=True, default="")
    position = models.PositiveSmallIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "room plan item"
        ordering = ["position", "-updated_at", "id"]

    def __str__(self) -> str:
        return self.title

    @property
    def estimated_total(self) -> Decimal:
        return (self.quantity * self.estimated_unit_cost).quantize(Decimal("0.01"))

    @property
    def effective_cost(self) -> Decimal:
        if self.status == self.Status.COMPLETED and self.actual_cost is not None:
            return self.actual_cost
        return self.estimated_total


class RoomPlanProduct(HouseholdBaseModel):
    """A candidate purchase for a room plan item — the shopping list behind "New sofa".

    A plan item used to carry a single `link_url`, which could not answer "which of the three
    we were looking at?". Each product is one option: what it is, where to buy it, what it
    costs and what it looks like.

    Images are stored as a URL rather than an upload, so adding an option is a copy-paste from
    a retailer's page. Note that rendering one makes the viewer's browser request the image
    from that third-party host.

    Marking an option `is_chosen` copies its price onto the parent plan item, so room and
    whole-house estimates reflect the option actually picked. Only one option per item can be
    chosen at a time.
    """

    plan_item = models.ForeignKey(
        RoomPlanItem, on_delete=models.CASCADE, related_name="products"
    )
    title = models.CharField(max_length=255)
    url = models.CharField(max_length=500, blank=True, default="")
    image_url = models.CharField(max_length=500, blank=True, default="")
    retailer = models.CharField(max_length=120, blank=True, default="")
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("1.00"),
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    is_chosen = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")
    position = models.PositiveSmallIntegerField(default=0)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "room plan product"
        ordering = ["position", "id"]

    def __str__(self) -> str:
        return self.title

    @property
    def total_cost(self) -> Decimal:
        return (self.quantity * self.unit_cost).quantize(Decimal("0.01"))


class InsurancePolicy(HouseholdBaseModel):
    """Home-related cover, mirrored into Solace as a linked recurring bill.

    Homestead owns the policy details and renewal workflow. Solace receives the premium,
    provider and renewal date through the event boundary so it can include the cost in the
    household budget without either node importing the other's models (D4).
    """

    class PolicyType(models.TextChoices):
        BUILDING = "building", "Building"
        CONTENTS = "contents", "Contents"
        BUILDING_CONTENTS = "building_contents", "Building & contents"
        LANDLORD = "landlord", "Landlord"
        MORTGAGE_PROTECTION = "mortgage_protection", "Mortgage protection"
        OTHER = "other", "Other"

    class BillingCycle(models.TextChoices):
        WEEKLY = "weekly", "Weekly"
        FORTNIGHTLY = "fortnightly", "Fortnightly"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        HALF_YEARLY = "half_yearly", "Every 6 months"
        YEARLY = "yearly", "Yearly"
        OTHER = "other", "Other"

    name = models.CharField(max_length=200)
    policy_type = models.CharField(
        max_length=30, choices=PolicyType.choices, default=PolicyType.BUILDING_CONTENTS
    )
    provider = models.CharField(max_length=200, blank=True, default="")
    policy_number = models.CharField(max_length=160, blank=True, default="")
    premium_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    billing_cycle = models.CharField(
        max_length=20, choices=BillingCycle.choices, default=BillingCycle.YEARLY
    )
    next_renewal_at = models.DateTimeField(null=True, blank=True)
    recurrence_rule = models.CharField(max_length=512, blank=True, default="")
    standard_excess = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    additional_excesses = models.TextField(blank=True, default="")
    coverage_summary = models.TextField(blank=True, default="")
    contact_phone = models.CharField(max_length=50, blank=True, default="")
    portal_url = models.CharField(max_length=500, blank=True, default="")
    is_active = models.BooleanField(default=True)
    solace_bill_ref = models.PositiveBigIntegerField(null=True, blank=True, editable=False)
    notes = models.TextField(blank=True, default="")
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.SENSITIVE
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "insurance policy"
        verbose_name_plural = "insurance policies"
        ordering = ["next_renewal_at", "name"]

    def __str__(self) -> str:
        return self.name


class HouseholdCost(HouseholdBaseModel):
    """A recurring home cost/account, mirrored into a linked Solace bill."""

    class CostType(models.TextChoices):
        RATES = "rates", "Council rates"
        WATER = "water", "Water"
        GAS = "gas", "Gas"
        ELECTRICITY = "electricity", "Electricity"
        MORTGAGE = "mortgage", "Mortgage / rent"
        BODY_CORPORATE = "body_corporate", "Body corporate / strata"
        WASTE = "waste", "Waste"
        INTERNET = "internet", "Internet"
        OTHER = "other", "Other"

    class BillingCycle(models.TextChoices):
        WEEKLY = "weekly", "Weekly"
        FORTNIGHTLY = "fortnightly", "Fortnightly"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        HALF_YEARLY = "half_yearly", "Every 6 months"
        YEARLY = "yearly", "Yearly"
        VARIABLE = "variable", "Variable / usage based"
        OTHER = "other", "Other"

    name = models.CharField(max_length=200)
    cost_type = models.CharField(max_length=30, choices=CostType.choices, default=CostType.OTHER)
    provider = models.CharField(max_length=200, blank=True, default="")
    account_number = models.CharField(max_length=160, blank=True, default="")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    billing_cycle = models.CharField(
        max_length=20, choices=BillingCycle.choices, default=BillingCycle.QUARTERLY
    )
    next_due_at = models.DateTimeField(null=True, blank=True)
    recurrence_rule = models.CharField(max_length=512, blank=True, default="")
    is_active = models.BooleanField(default=True)
    solace_bill_ref = models.PositiveBigIntegerField(null=True, blank=True, editable=False)
    notes = models.TextField(blank=True, default="")
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.SENSITIVE
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "household cost"
        ordering = ["next_due_at", "name"]

    def __str__(self) -> str:
        return self.name
