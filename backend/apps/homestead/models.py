"""homestead models — the household's home/property hub (Node Spec 25).

V1 slice: the property record (with practical emergency info), recurring/one-off maintenance,
appliances + warranties, a service-provider directory, and a lightweight improvements list.

Design intent (owner, 2026-07-21): Homestead is an *aggregating* home hub. When the financial
node (Solace) and the Projects node exist, Homestead surfaces the house-relevant slices of them
(rates/bills; house projects) and deep-links to the full record — always via the events bus and
read-time aggregation, never by importing another node's models (D4). Two dormant hooks live
here now: money is deliberately absent (comes from Solace) and `Improvement.project_ref` links
an improvement to a future full Project.

All models inherit HouseholdBaseModel (household scoping, audit, soft-delete). Maintenance and
improvement dates mirror to the shared calendar via the scheduling helper only (D7); recurring
maintenance carries an RRULE (D8). Nothing household-specific is hardcoded (D15).
"""
from __future__ import annotations

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
