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
        GENERAL = "general", "General"

    title = models.CharField(max_length=255)
    list_type = models.CharField(
        max_length=20, choices=ListType.choices, default=ListType.GENERAL
    )
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "atlas list"
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.title


class AtlasListItem(HouseholdBaseModel):
    """An item within an AtlasList, optionally assigned and completable."""

    atlas_list = models.ForeignKey(
        AtlasList, on_delete=models.CASCADE, related_name="items"
    )
    title = models.CharField(max_length=255)
    notes = models.TextField(blank=True, default="")
    quantity = models.CharField(max_length=50, blank=True, default="")  # grocery/shopping (e.g. "2", "500g")
    position = models.PositiveIntegerField(default=0)
    due_at = models.DateTimeField(null=True, blank=True)
    assigned_to_person = models.ForeignKey(
        "people.Person",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_list_items",
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


class AtlasReminder(CalendarSyncMixin, HouseholdBaseModel):
    """A reminder, optionally dated. Dated reminders sync to the shared calendar (D7)."""

    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")
    due_at = models.DateTimeField(null=True, blank=True)
    recurrence_rule = models.CharField(max_length=512, blank=True, default="")
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
            "description": self.body,
            "recurrence_rule": self.recurrence_rule,
            "visibility": self.visibility,
            "sensitivity": self.sensitivity,
        }

    def get_calendar_node_key(self) -> str:
        return "atlas"
