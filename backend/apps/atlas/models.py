"""atlas models — notes, lists, list items, reminders (D18, Architecture §8).

Atlas is the one fully-built node in Milestone 1. All four models inherit
HouseholdBaseModel so they get household scoping, audit fields, and soft-delete.
AtlasReminder additionally implements CalendarSyncMixin so dated reminders appear
on the shared calendar without ever writing CalendarEvent rows directly (D7).
"""
from __future__ import annotations

from django.conf import settings
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


class AtlasNote(HouseholdBaseModel):
    """A freeform note, optionally private or role-restricted."""

    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )
    sensitivity = models.CharField(
        max_length=20, choices=Sensitivity.choices, default=Sensitivity.NORMAL
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "atlas note"
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.title


class AtlasList(HouseholdBaseModel):
    """A named list (to-do, grocery, checklist, etc.)."""

    class ListType(models.TextChoices):
        TODO = "todo", "To Do"
        GROCERY = "grocery", "Grocery"
        CHECKLIST = "checklist", "Checklist"
        SHOPPING = "shopping", "Shopping"
        WISHLIST = "wishlist", "Wish list"
        GENERAL = "general", "General"

    title = models.CharField(max_length=255)
    list_type = models.CharField(
        max_length=20, choices=ListType.choices, default=ListType.GENERAL
    )
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )
    owner_person = models.ForeignKey(
        "people.Person", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="owned_atlas_lists",
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "atlas list"
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.title


class AtlasListItem(CalendarSyncMixin, HouseholdBaseModel):
    """An item within an AtlasList, optionally assigned and completable."""

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    atlas_list = models.ForeignKey(
        AtlasList, on_delete=models.CASCADE, related_name="items"
    )
    title = models.CharField(max_length=255)
    notes = models.TextField(blank=True, default="")
    quantity = models.CharField(max_length=50, blank=True, default="")  # grocery/shopping (e.g. "2", "500g")
    # Blank means "not set" rather than a real priority — only the shopping-list UI surfaces
    # this, so a todo/grocery/checklist item left blank never shows a fabricated priority.
    priority = models.CharField(max_length=10, choices=Priority.choices, blank=True, default="")
    product_url = models.CharField(max_length=1000, blank=True, default="")
    source_image_url = models.CharField(max_length=1000, blank=True, default="")
    image_attachment = models.ForeignKey(
        "attachments.Attachment", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="atlas_product_items",
    )
    retailer = models.CharField(max_length=160, blank=True, default="")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, blank=True, default="AUD")
    imported_at = models.DateTimeField(null=True, blank=True)
    position = models.PositiveIntegerField(default=0)
    due_at = models.DateTimeField(null=True, blank=True)
    calendar_event_id = models.PositiveBigIntegerField(null=True, blank=True)
    assigned_to_people = models.ManyToManyField(
        "people.Person",
        blank=True,
        related_name="assigned_list_items",
        help_text=(
            "Who this is for. Empty means the whole household — a household job with no "
            "particular owner. Several people means each of them, not one of them."
        ),
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="completed_list_items",
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "atlas list item"
        ordering = ["position", "id"]

    def __str__(self) -> str:
        return self.title

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None

    def get_calendar_data(self) -> dict | None:
        if not self.due_at or self.completed_at:
            return None
        return {
            "title": self.title,
            "start_at": self.due_at,
            "description": self.notes,
            "event_kind": "task",
            "visibility": self.atlas_list.visibility,
            "sensitivity": "normal",
            "assigned_to_person_ids": list(self.assigned_to_people.values_list("id", flat=True)),
        }

    def get_calendar_node_key(self) -> str:
        return "atlas"


class AtlasListSuggestion(HouseholdBaseModel):
    """A proposed item another member may accept into an owned personal list."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DISMISSED = "dismissed", "Dismissed"

    atlas_list = models.ForeignKey(AtlasList, on_delete=models.CASCADE, related_name="suggestions")
    suggested_by_person = models.ForeignKey(
        "people.Person", on_delete=models.CASCADE, related_name="atlas_list_suggestions"
    )
    title = models.CharField(max_length=255)
    notes = models.TextField(blank=True, default="")
    product_url = models.CharField(max_length=1000, blank=True, default="")
    source_image_url = models.CharField(max_length=1000, blank=True, default="")
    retailer = models.CharField(max_length=160, blank=True, default="")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, blank=True, default="AUD")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    accepted_item = models.ForeignKey(
        AtlasListItem, null=True, blank=True, on_delete=models.SET_NULL, related_name="accepted_suggestion"
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["-created_at", "-id"]


class AtlasReminder(CalendarSyncMixin, HouseholdBaseModel):
    """A reminder, optionally dated. Dated reminders sync to the shared calendar (D7)."""

    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")
    due_at = models.DateTimeField(null=True, blank=True)
    is_all_day = models.BooleanField(default=False)  # due on a date, no specific time
    recurrence_rule = models.CharField(max_length=512, blank=True, default="")
    assigned_to_people = models.ManyToManyField(
        "people.Person", blank=True, related_name="assigned_reminders",
        help_text="Who should receive this reminder. Empty means the whole household.",
    )
    notifications_enabled = models.BooleanField(
        default=True,
        help_text="Allow the shared notification scheduler to notify recipients for this reminder.",
    )
    calendar_event_id = models.PositiveBigIntegerField(null=True, blank=True)
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )
    sensitivity = models.CharField(
        max_length=20, choices=Sensitivity.choices, default=Sensitivity.NORMAL
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "atlas reminder"
        ordering = ["due_at", "-updated_at"]

    def __str__(self) -> str:
        return self.title

    # --- CalendarSyncMixin contract ---

    def get_calendar_data(self) -> dict | None:
        if not self.due_at:
            return None
        return {
            "title": self.title,
            "start_at": self.due_at,
            "is_all_day": self.is_all_day,
            "description": self.body,
            "recurrence_rule": self.recurrence_rule,
            "assigned_to_person_ids": list(self.assigned_to_people.values_list("id", flat=True)),
            "visibility": self.visibility,
            "sensitivity": self.sensitivity,
        }

    def get_calendar_node_key(self) -> str:
        return "atlas"


class AtlasContact(HouseholdBaseModel):
    """A friend/relative kept without manufacturing a login-backed Person."""

    name = models.CharField(max_length=255)
    date_of_birth = models.DateField()
    relationship = models.CharField(max_length=120, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    linked_person = models.OneToOneField(
        "people.Person", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="atlas_contact",
    )
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
