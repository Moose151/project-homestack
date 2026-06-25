"""notifications models — per-user dashboard notifications (shared infrastructure).

Notifications are addressed to a **user** (the login holder) — e.g. a child's linked user gets
"Task approved". This is shared infrastructure that nodes call directly (like audit/scheduling),
not a node itself, so importing `notifications.services` from a node does not breach D4.
"""
from __future__ import annotations

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
