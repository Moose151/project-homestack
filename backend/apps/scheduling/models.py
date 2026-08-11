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

    class EventKind(models.TextChoices):
        EVENT = "event", "Event"
        APPOINTMENT = "appointment", "Appointment"
        BIRTHDAY = "birthday", "Birthday"
        HOLIDAY = "holiday", "Holiday"
        TASK = "task", "Task / deadline"

    title = models.CharField(max_length=255)
    event_kind = models.CharField(max_length=16, choices=EventKind.choices, default=EventKind.EVENT)
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

    assigned_to_people = models.ManyToManyField(
        "people.Person",
        blank=True,
        related_name="assigned_calendar_events",
        help_text=(
            "Who this is for. Empty means the whole household — a household job with no "
            "particular owner. Several people means each of them, not one of them."
        ),
    )
    hidden_from_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="hidden_calendar_events",
        help_text="Users explicitly excluded from surprise shared events.",
    )
    colour = models.CharField(max_length=7, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    provider = models.CharField(max_length=160, blank=True, default="")
    contact = models.CharField(max_length=255, blank=True, default="")

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


class RotatingSchedule(HouseholdBaseModel):
    """A repeating two-state calendar layer, expanded virtually for a requested range.

    ``cycle_pattern`` is the single source of truth: P selects ``primary_label`` and S
    selects ``secondary_label``. It deliberately does not create one CalendarEvent per
    day. Date-specific changes live in RotatingScheduleException instead (D23).
    """

    title = models.CharField(max_length=100)
    primary_label = models.CharField(max_length=100, default="With us")
    secondary_label = models.CharField(max_length=100, default="Other home")
    anchor_date = models.DateField()
    cycle_pattern = models.CharField(max_length=62, default="PPSSPPPSSPPSSS")
    primary_colour = models.CharField(max_length=7, default="#3F7D65")
    secondary_colour = models.CharField(max_length=7, default="#8A718E")
    people = models.ManyToManyField(
        "people.Person",
        blank=True,
        related_name="rotating_schedules",
    )
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.HOUSEHOLD,
    )
    is_active = models.BooleanField(default=True)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title

    @property
    def cycle_length(self) -> int:
        return len(self.cycle_pattern)

    def state_for_date(self, value) -> str:
        offset = (value - self.anchor_date).days % self.cycle_length
        return "primary" if self.cycle_pattern[offset] == "P" else "secondary"


class RotatingScheduleException(HouseholdBaseModel):
    """A one-day state override without altering the canonical rotation."""

    class State(models.TextChoices):
        PRIMARY = "primary", "Primary"
        SECONDARY = "secondary", "Secondary"

    schedule = models.ForeignKey(
        RotatingSchedule,
        on_delete=models.CASCADE,
        related_name="exceptions",
    )
    date = models.DateField()
    state = models.CharField(max_length=12, choices=State.choices)
    note = models.CharField(max_length=255, blank=True, default="")

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(
                fields=["schedule", "date"],
                name="unique_rotating_schedule_exception_date",
            )
        ]

    def __str__(self) -> str:
        return f"{self.schedule}: {self.date} → {self.state}"
