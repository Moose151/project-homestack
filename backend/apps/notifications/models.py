"""notifications models — per-user dashboard notifications (shared infrastructure).

Notifications are addressed to a **user** (the login holder) — e.g. a child's linked user gets
"Task approved". This is shared infrastructure that nodes call directly (like audit/scheduling),
not a node itself, so importing `notifications.services` from a node does not breach D4.
"""
from __future__ import annotations

from datetime import time

from django.conf import settings
from django.db import models

from apps.core.models import AllObjectsManager, HouseholdBaseModel, HouseholdManager


class Notification(HouseholdBaseModel):
    class Level(models.TextChoices):
        INFO = "info", "Info"
        SUCCESS = "success", "Success"
        WARNING = "warning", "Warning"
        DANGER = "danger", "Danger"

    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=120)
    message = models.CharField(max_length=255)
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.INFO)
    source_node = models.CharField(max_length=40, blank=True, default="")
    action_url = models.CharField(max_length=255, blank=True, default="")
    is_read = models.BooleanField(default=False, db_index=True)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "notification"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.recipient_user_id}: {self.title}"


class NotificationCategory(models.TextChoices):
    """The fixed taxonomy from docs/32_Core_Notifications_and_Push.md §3.

    A category passed as `""` (the default on every existing call site) bypasses preferences
    entirely — it always creates the in-app row, exactly matching pre-preference behaviour, so
    nothing already shipped changes until a node deliberately opts into a category.
    """

    APPOINTMENTS = "appointments", "Appointments & events"
    ASSIGNED_TASKS = "assigned_tasks", "Assigned to-dos & reminders"
    HOUSEHOLD_ACTIVITY = "household_activity", "Household activity"
    HOME_MAINTENANCE = "home_maintenance", "Home & maintenance"
    MERIDIAN = "meridian", "Meridian"
    FITNESS = "fitness", "Fitness"
    BOOKS = "books", "Books"
    TRAVEL = "travel", "Travel"
    WISH_PRICE_ALERTS = "wish_price_alerts", "Wish & price alerts"
    COUNTDOWN = "countdown", "Countdown"
    CORNERS = "corners", "Corners"
    ACCOUNT = "account", "Account & security"


# Categories where "assigned to me only" vs "everyone's" is a meaningful distinction
# (docs/32 §3). Exposed so the preferences UI only offers the toggle where it applies.
MINE_ONLY_CATEGORIES = {NotificationCategory.APPOINTMENTS, NotificationCategory.ASSIGNED_TASKS}

# Categories that default to push off / in-app on (docs/32 §3) — everything else defaults both on.
PUSH_OFF_BY_DEFAULT = {NotificationCategory.HOUSEHOLD_ACTIVITY, NotificationCategory.WISH_PRICE_ALERTS}


class NotificationPreference(HouseholdBaseModel):
    """Per-user, per-category in-app/push toggle. Missing row = defaults above apply."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preferences"
    )
    category = models.CharField(max_length=30, choices=NotificationCategory.choices)
    in_app_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    mine_only = models.BooleanField(
        default=False,
        help_text="Only meaningful for categories in MINE_ONLY_CATEGORIES; ignored otherwise.",
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "notification preference"
        constraints = [
            models.UniqueConstraint(fields=["user", "category"], name="unique_user_category_preference")
        ]

    def __str__(self) -> str:
        return f"{self.user_id}: {self.category}"


class UserNotificationSettings(HouseholdBaseModel):
    """One row per user: quiet hours and the daily 'morning' time (Household-local, D-32 §2)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_settings"
    )
    quiet_start = models.TimeField(null=True, blank=True)
    quiet_end = models.TimeField(null=True, blank=True)
    morning_time = models.TimeField(default=time(8, 0))

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "user notification settings"

    def __str__(self) -> str:
        return f"{self.user_id} notification settings"


class PushDevice(HouseholdBaseModel):
    """One browser Web Push subscription (docs/32 §4/§10). Several rows per user is normal —
    phone, laptop, tablet each subscribe separately."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_devices"
    )
    endpoint = models.CharField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    label = models.CharField(max_length=120, blank=True, default="")
    user_agent = models.CharField(max_length=255, blank=True, default="")
    last_seen_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "push device"
        ordering = ["-last_seen_at"]

    def __str__(self) -> str:
        return self.label or self.endpoint[:40]
