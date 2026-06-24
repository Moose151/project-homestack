"""scheduling.CalendarEvent — the calendar store for HomeStack (D7, D8).

All dated entries (standalone events + node-backed reminders, travel bookings, etc.)
live in this table. Nodes never write here directly — they call the scheduling helper
(D7). Recurrence is stored as an RRULE string on the owning record and copied here
for display; full RRULE expansion is deferred (D8).
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.core.models import AllObjectsManager, HouseholdBaseModel, HouseholdManager


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


class CalendarEvent(HouseholdBaseModel):
    """A calendar entry. Standalone events are created via the API; synced events are
    created and owned by a node record via the scheduling helper (source_* fields set).

    Write path: API → services.create_event / helpers.sync_event_for → this table.
    Never: CalendarEvent.objects.create() from a node service directly.
    """

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(null=True, blank=True)
    is_all_day = models.BooleanField(default=False)
    timezone = models.CharField(max_length=64, blank=True, default="")
    recurrence_rule = models.CharField(max_length=512, blank=True, default="")

    # Source record link — set when this event is backed by a node record.
    source_node = models.ForeignKey(
        "nodes.Node",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="calendar_events",
    )
    source_record_type = models.CharField(max_length=100, blank=True, default="")
    source_record_id = models.PositiveBigIntegerField(null=True, blank=True)

    assigned_to_person = models.ForeignKey(
        "people.Person",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="calendar_events",
    )
    colour = models.CharField(max_length=7, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")

    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.HOUSEHOLD,
    )
    sensitivity = models.CharField(
        max_length=20,
        choices=Sensitivity.choices,
        default=Sensitivity.NORMAL,
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "calendar event"
        verbose_name_plural = "calendar events"
        ordering = ["start_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def is_synced(self) -> bool:
        """True when this event is owned by a node record (not a standalone event)."""
        return bool(self.source_record_type and self.source_record_id)
