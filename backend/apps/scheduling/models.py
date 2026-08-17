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

    # --- Source-managed mirror metadata (Calendar Sources) ---
    # Set only for entries a CalendarSource owns. A hand-made HomeStack event leaves every one
    # of these empty and behaves exactly as it always has.
    calendar_source = models.ForeignKey(
        "scheduling.CalendarSource",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="events",
    )
    # The feed's own UID (or a provider-derived stable key). Identity for re-sync: the same UID
    # updates its existing event rather than creating a second one, so a fixture that moves
    # venue or kick-off time moves instead of duplicating.
    external_uid = models.CharField(max_length=255, blank=True, default="")
    # iCalendar SEQUENCE, when the feed provides one.
    external_sequence = models.IntegerField(null=True, blank=True)
    # The source's sync_revision when this event was last seen in the feed. An event whose
    # revision falls behind has disappeared upstream.
    last_seen_revision = models.PositiveIntegerField(null=True, blank=True)
    # A multi-day range (school term, school holidays) rendered as one banner rather than one
    # event per day.
    is_range = models.BooleanField(default=False)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    @property
    def is_source_managed(self) -> bool:
        """Owned by a CalendarSource, so the local edit form must not pretend otherwise."""
        return self.calendar_source_id is not None

    @property
    def is_externally_managed(self) -> bool:
        """Owned by something other than the Calendar itself — a node record or a source.

        The one question every write path must ask. ``is_synced`` alone is not it: a
        source-managed entry leaves ``source_record_*`` empty, so checking only that let a
        subscribed fixture or a public holiday be edited and deleted through the events API,
        with the next sync silently reinstating it.
        """
        return self.is_synced or self.is_source_managed

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


class CalendarSource(HouseholdBaseModel):
    """A managed origin of calendar entries that is not a hand-made HomeStack event.

    Public holidays, school terms and subscribed ICS feeds are all the same shape of problem:
    someone else owns the dates, HomeStack mirrors them, and the mirror has to survive being
    refreshed. Modelling them as one extensible source rather than special cases inside the
    Calendar page means a new provider is a new row and a new provider class, not another
    Calendar redesign.

    ``kind`` says how the source is fed; ``provider`` says who feeds it. Both are validated
    against the registry in apps.scheduling.sources.registry — ``settings_json`` is never free
    JSON, it is validated per provider, because these values decide what gets fetched.
    """

    class Kind(models.TextChoices):
        HOLIDAYS = "holidays", "Public holidays"
        SCHOOL = "school", "School calendar"
        SUBSCRIPTION = "subscription", "Subscribed calendar"
        IMPORT = "import", "Imported calendar"

    class Status(models.TextChoices):
        IDLE = "idle", "Never synced"
        OK = "ok", "Synced"
        ERROR = "error", "Failed"

    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    # Provider slug within the kind, e.g. "au_holidays", "au_school_terms", "ics".
    provider = models.CharField(max_length=40)
    is_enabled = models.BooleanField(default=True)
    colour = models.CharField(max_length=7, blank=True, default="")
    category = models.CharField(max_length=40, blank=True, default="")
    # Only meaningful for fetched sources. webcal:// is normalised to https:// on save.
    url = models.URLField(max_length=500, blank=True, default="")
    settings_json = models.JSONField(default=dict, blank=True)

    show_on_calendar = models.BooleanField(default=True)
    show_in_upcoming = models.BooleanField(default=True)
    # Off by default and deliberately so: subscribing to a season of fixtures must not push a
    # notification for every one of them.
    notifications_enabled = models.BooleanField(default=False)

    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    sync_status = models.CharField(max_length=10, choices=Status.choices, default=Status.IDLE)
    sync_error = models.CharField(max_length=500, blank=True, default="")
    # Monotonic counter bumped at the start of each sync. Events carry the revision they were
    # last seen in, which is how a disappeared entry is detected without a second query.
    sync_revision = models.PositiveIntegerField(default=0)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "calendar source"
        verbose_name_plural = "calendar sources"
        ordering = ["kind", "name"]

    def __str__(self) -> str:
        return self.name


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
