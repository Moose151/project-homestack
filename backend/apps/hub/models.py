"""hub models — widget catalogue and per-household/user configuration."""
from __future__ import annotations

from django.conf import settings
from django.db import models


class HubWidget(models.Model):
    """A widget type available to households (catalogue / seed data)."""

    key = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    source_node = models.ForeignKey(
        "nodes.Node",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="hub_widgets",
    )
    supports_kiosk = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    always_visible = models.BooleanField(
        default=False,
        help_text=(
            "Ambient widgets (clock, quick add, countdown) render even with no content. "
            "Every other widget is dropped from the Hub while it has nothing to show."
        ),
    )

    class Meta:
        ordering = ["display_order", "key"]

    def __str__(self) -> str:
        return self.name


class HouseholdHubWidget(models.Model):
    """Household-level widget configuration (which widgets are enabled, order, size)."""

    household = models.ForeignKey(
        "core.Household", on_delete=models.CASCADE, related_name="hub_widgets"
    )
    widget = models.ForeignKey(HubWidget, on_delete=models.CASCADE)
    is_enabled = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    size = models.CharField(
        max_length=10,
        choices=[("small", "Small"), ("medium", "Medium"), ("large", "Large")],
        default="medium",
    )
    settings_json = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("household", "widget")]
        ordering = ["display_order"]

    def __str__(self) -> str:
        return f"{self.household} — {self.widget}"


class UserHubWidget(models.Model):
    """Per-user overrides — a user can hide or reorder widgets."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hub_widgets"
    )
    widget = models.ForeignKey(HubWidget, on_delete=models.CASCADE)
    is_enabled = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    settings_json = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("user", "widget")]
        ordering = ["display_order"]

    def __str__(self) -> str:
        return f"{self.user} — {self.widget}"


class HubUpcomingDismissal(models.Model):
    """A User snoozing one Calendar projection out of their Upcoming feed.

    This is presentation state only: the Calendar event and its owning domain record remain
    untouched.  The event foreign key deliberately cascades so completion/deletion cannot leave
    dismissal debris behind.

    Snoozes expire (``hidden_until``) rather than lasting forever. A permanent hide is a
    one-way door: the Undo toast lasts seconds, and nothing else in the product lists what a
    User has hidden, so an accidental tap would silently remove something from their Dashboard
    with no way back. Expiry makes the worst case "it reappears tomorrow" instead.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hub_upcoming_dismissals",
    )
    event = models.ForeignKey(
        "scheduling.CalendarEvent",
        on_delete=models.CASCADE,
        related_name="hub_dismissals",
    )
    dismissed_at = models.DateTimeField(auto_now_add=True)
    hidden_until = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "event"], name="hub_unique_upcoming_dismissal"
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} snoozed event {self.event_id} until {self.hidden_until}"
