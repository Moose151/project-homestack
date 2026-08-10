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
        POOL = "pool", "Pool / spa"
        RENEWAL = "renewal", "Renewal / admin"
        GENERAL = "general", "General"

    appliance = models.ForeignKey(
        Appliance, on_delete=models.SET_NULL, null=True, blank=True, related_name="maintenance_tasks"
    )
    # Pool care is ordinary maintenance: recurring, calendar-synced and completed the same way.
    # The link exists so the pool screen can show its own jobs, not to fork the behaviour.
    pool = models.ForeignKey(
        "homestead.Pool", on_delete=models.CASCADE, null=True, blank=True, related_name="care_tasks"
    )
    provider = models.ForeignKey(
        ServiceProvider, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    assigned_to_people = models.ManyToManyField(
        "people.Person",
        blank=True,
        related_name="assigned_maintenance_tasks",
        help_text=(
            "Who this is for. Empty means the whole household — a household job with no "
            "particular owner. Several people means each of them, not one of them."
        ),
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

    assigned_to_people = models.ManyToManyField(
        "people.Person",
        blank=True,
        related_name="assigned_improvements",
        help_text=(
            "Who this is for. Empty means the whole household — a household job with no "
            "particular owner. Several people means each of them, not one of them."
        ),
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
    """One wanted purchase, maintenance job, renovation or upgrade for a room.

    A job is either a **single item** — its products are alternatives you compare and pick
    one of, and the chosen one's price is the estimate — or a **project**, where its products
    are parts that are all required and their prices sum (owner, 2026-08-09). Same rows on
    screen; the mode decides the arithmetic.
    """

    class PlanMode(models.TextChoices):
        SINGLE = "single", "Single item"
        PROJECT = "project", "Project"

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
    plan_mode = models.CharField(
        max_length=10,
        choices=PlanMode.choices,
        default=PlanMode.SINGLE,
        help_text="single: products are alternatives. project: products are parts that sum.",
    )
    assigned_to_people = models.ManyToManyField(
        "people.Person",
        blank=True,
        related_name="assigned_room_plan_items",
        help_text=(
            "Who this is for. Empty means the whole household — a household job with no "
            "particular owner. Several people means each of them, not one of them."
        ),
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
    def is_project(self) -> bool:
        return self.plan_mode == self.PlanMode.PROJECT

    @property
    def estimated_total(self) -> Decimal:
        """What the job is expected to cost.

        A project costs the sum of its parts — that number is always current, so a project
        has no separately typed estimate to go stale. A single item costs its own quantity
        times unit price, which the chosen option keeps up to date.
        """
        if self.is_project:
            return sum(
                (product.total_cost for product in self.products.all()),
                Decimal("0.00"),
            ).quantize(Decimal("0.01"))
        return (self.quantity * self.estimated_unit_cost).quantize(Decimal("0.01"))

    @property
    def parts_bought_count(self) -> int:
        return sum(1 for product in self.products.all() if product.is_purchased)

    @property
    def parts_count(self) -> int:
        return len(self.products.all())

    @property
    def spent_cost(self) -> Decimal:
        """Already paid: the actual price of each bought part, falling back to its estimate."""
        if not self.is_project:
            return self.actual_cost or Decimal("0.00")
        return sum(
            (
                product.actual_cost if product.actual_cost is not None else product.total_cost
                for product in self.products.all()
                if product.is_purchased
            ),
            Decimal("0.00"),
        ).quantize(Decimal("0.01"))

    @property
    def remaining_cost(self) -> Decimal:
        """Still to buy — the estimate of every part not yet ticked off."""
        if not self.is_project:
            return Decimal("0.00") if self.status == self.Status.COMPLETED else self.estimated_total
        return sum(
            (product.total_cost for product in self.products.all() if not product.is_purchased),
            Decimal("0.00"),
        ).quantize(Decimal("0.01"))

    @property
    def effective_cost(self) -> Decimal:
        if self.is_project:
            return (self.spent_cost + self.remaining_cost).quantize(Decimal("0.01"))
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
    is_chosen = models.BooleanField(
        default=False,
        help_text="Single-item jobs only: the alternative picked, whose price is the estimate.",
    )
    is_purchased = models.BooleanField(
        default=False, help_text="Project parts: already bought."
    )
    actual_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Total actually paid for this part, if it differed from the estimate.",
    )
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


class UtilityBill(HouseholdBaseModel):
    """One metered bill: what a utility charged, for which period, and how much was used.

    `HouseholdCost` answers "what do we pay for water and when is it due?" — the recurring
    account. This answers "what did we actually use?", one bill at a time, so the household can
    see whether usage is drifting rather than only whether the bill was paid.

    Billing periods are not equal lengths — a 92-day quarter against an 88-day one is not a
    like-for-like comparison — so every derived figure here is per day. Nothing is stored that
    can be calculated, which keeps a corrected period or amount honest everywhere at once.

    Household-visible by default (owner, 2026-08-10): usage is something the whole house should
    be able to look at. The recurring account and its policy/reference numbers stay behind the
    costs & cover gate.
    """

    class UtilityType(models.TextChoices):
        ELECTRICITY = "electricity", "Electricity"
        WATER = "water", "Water"
        GAS = "gas", "Gas"
        OTHER = "other", "Other"

    class Unit(models.TextChoices):
        KWH = "kwh", "kWh"
        KL = "kl", "kL"
        LITRES = "litres", "L"
        CUBIC_M = "m3", "m³"
        MJ = "mj", "MJ"
        THERMS = "therms", "therms"
        OTHER = "other", "units"

    # What a new bill of each type is measured in unless the household says otherwise. Metric
    # defaults; the unit is stored per bill so a household on m³ or therms is not fighting it.
    DEFAULT_UNITS = {
        UtilityType.ELECTRICITY: Unit.KWH,
        UtilityType.WATER: Unit.KL,
        UtilityType.GAS: Unit.MJ,
        UtilityType.OTHER: Unit.OTHER,
    }

    utility_type = models.CharField(
        max_length=20, choices=UtilityType.choices, default=UtilityType.ELECTRICITY
    )
    provider = models.CharField(max_length=200, blank=True, default="")
    period_start = models.DateField()
    period_end = models.DateField()
    usage_amount = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="How much was used over the period, in `usage_unit`.",
    )
    usage_unit = models.CharField(max_length=10, choices=Unit.choices, default=Unit.KWH)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Total charged for the period, including supply charges.",
    )
    is_estimated = models.BooleanField(
        default=False, help_text="The meter was estimated rather than read."
    )
    notes = models.TextField(blank=True, default="")
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "utility bill"
        ordering = ["-period_end", "-id"]
        indexes = [models.Index(fields=["utility_type", "period_end"])]

    def __str__(self) -> str:
        return f"{self.get_utility_type_display()} {self.period_start:%Y-%m-%d}–{self.period_end:%Y-%m-%d}"

    @property
    def unit_label(self) -> str:
        return self.Unit(self.usage_unit).label

    @property
    def days(self) -> int:
        """Days billed, counting both end dates — a 1st-to-31st bill is 31 days, not 30."""
        return (self.period_end - self.period_start).days + 1

    @property
    def daily_usage(self) -> Decimal:
        return (self.usage_amount / self.days).quantize(Decimal("0.001"))

    @property
    def daily_cost(self) -> Decimal:
        return (self.amount / self.days).quantize(Decimal("0.01"))

    @property
    def unit_cost(self) -> Decimal | None:
        """What each unit effectively cost, supply charges included. None if nothing was used."""
        if not self.usage_amount:
            return None
        return (self.amount / self.usage_amount).quantize(Decimal("0.0001"))


class Pool(HouseholdBaseModel):
    """A pool or spa on the property, its equipment, and how it is sanitised.

    Kept general (D15): the target water bands and the starter care schedule come from
    `pool_care.py` and vary by sanitiser and surface, not by whose pool it is. Care jobs are
    ordinary `MaintenanceTask` rows pointing back here, so a pool job recurs, reaches the
    Calendar (D7/D8) and is completed exactly like any other home job.
    """

    class Kind(models.TextChoices):
        POOL = "pool", "Swimming pool"
        SPA = "spa", "Spa / hot tub"
        SWIM_SPA = "swim_spa", "Swim spa"
        PLUNGE = "plunge", "Plunge pool"

    class Sanitiser(models.TextChoices):
        SALTWATER = "saltwater", "Saltwater (chlorinator)"
        CHLORINE = "chlorine", "Manually chlorinated"
        MINERAL = "mineral", "Mineral / magnesium"
        BROMINE = "bromine", "Bromine"
        OTHER = "other", "Other"

    class Surface(models.TextChoices):
        CONCRETE = "concrete", "Concrete / rendered"
        FIBREGLASS = "fibreglass", "Fibreglass"
        VINYL_LINER = "vinyl_liner", "Vinyl liner"
        TILED = "tiled", "Fully tiled"
        OTHER = "other", "Other"

    class FilterType(models.TextChoices):
        SAND = "sand", "Sand"
        CARTRIDGE = "cartridge", "Cartridge"
        GLASS = "glass", "Glass media"
        DE = "de", "Diatomaceous earth"
        OTHER = "other", "Other"

    room = models.ForeignKey(
        RoomArea, on_delete=models.SET_NULL, null=True, blank=True, related_name="pools"
    )
    name = models.CharField(max_length=160, default="Pool")
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.POOL)
    sanitiser = models.CharField(
        max_length=20, choices=Sanitiser.choices, default=Sanitiser.SALTWATER
    )
    surface = models.CharField(max_length=20, choices=Surface.choices, default=Surface.CONCRETE)
    filter_type = models.CharField(
        max_length=20, choices=FilterType.choices, default=FilterType.OTHER
    )
    volume_litres = models.PositiveIntegerField(null=True, blank=True)
    is_indoor = models.BooleanField(default=False)
    equipment_notes = models.TextField(
        blank=True, default="", help_text="Pump, filter and chlorinator models, settings, quirks."
    )
    notes = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "pool or spa"
        ordering = ["name", "id"]

    def __str__(self) -> str:
        return self.name

    @property
    def has_salt_cell(self) -> bool:
        return self.sanitiser in (self.Sanitiser.SALTWATER, self.Sanitiser.MINERAL)


class WaterTest(HouseholdBaseModel):
    """One set of water readings, so the household can see whether things are drifting.

    Every reading is optional: a weekly strip gives chlorine and pH, while the monthly shop test
    fills in the rest. Whether a number is in range is decided against `pool_care` targets at
    read time, not stored, so corrected guidance applies to old readings too.
    """

    pool = models.ForeignKey(Pool, on_delete=models.CASCADE, related_name="water_tests")
    tested_at = models.DateTimeField()
    free_chlorine = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    ph = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    total_alkalinity = models.DecimalField(max_digits=7, decimal_places=1, null=True, blank=True)
    calcium_hardness = models.DecimalField(max_digits=7, decimal_places=1, null=True, blank=True)
    cyanuric_acid = models.DecimalField(max_digits=7, decimal_places=1, null=True, blank=True)
    salt = models.DecimalField(max_digits=8, decimal_places=1, null=True, blank=True)
    water_temp_c = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "water test"
        ordering = ["-tested_at", "-id"]

    def __str__(self) -> str:
        return f"{self.pool.name} — {self.tested_at:%Y-%m-%d}"

    def reading_values(self) -> dict:
        return {
            "free_chlorine": self.free_chlorine, "ph": self.ph,
            "total_alkalinity": self.total_alkalinity, "calcium_hardness": self.calcium_hardness,
            "cyanuric_acid": self.cyanuric_acid, "salt": self.salt,
            "water_temp_c": self.water_temp_c,
        }
