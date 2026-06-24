"""backups models — Backup record tracking pg_dump + media tarballs (D17)."""
from django.db import models

from apps.core.models import HouseholdBaseModel


class Backup(HouseholdBaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"

    label = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    # Paths are relative to BACKUP_DIR
    db_file = models.CharField(max_length=500, blank=True)
    media_file = models.CharField(max_length=500, blank=True)
    db_checksum = models.CharField(max_length=64, blank=True)      # SHA-256 hex
    media_checksum = models.CharField(max_length=64, blank=True)   # SHA-256 hex
    size_bytes = models.BigIntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.label} ({self.status})"
