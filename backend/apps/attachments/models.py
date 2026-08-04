"""Shared attachment metadata and protected file storage (D11)."""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.core.models import HouseholdBaseModel


def attachment_upload_path(instance: "Attachment", _original_name: str) -> str:
    """Keep user-controlled names out of storage paths."""
    return f"attachments/{instance.household_id}/{instance.filename}"


class Attachment(HouseholdBaseModel):
    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        HOUSEHOLD = "household", "Household"
        ROLE_RESTRICTED = "role_restricted", "Role restricted"
        SENSITIVE = "sensitive", "Sensitive"

    class Sensitivity(models.TextChoices):
        NORMAL = "normal", "Normal"
        FINANCIAL = "financial", "Financial"
        HEALTH = "health", "Health"
        DOCUMENT = "document", "Document"
        PRIVATE = "private", "Private"

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_attachments",
    )
    filename = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    file_path = models.FileField(upload_to=attachment_upload_path, max_length=500)
    mime_type = models.CharField(max_length=255, blank=True, default="application/octet-stream")
    file_size = models.PositiveBigIntegerField()
    checksum = models.CharField(max_length=64)
    linked_node = models.ForeignKey(
        "nodes.Node",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="attachments",
    )
    linked_record_type = models.CharField(max_length=150, blank=True, default="")
    linked_record_id = models.PositiveBigIntegerField(null=True, blank=True)
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

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["household", "linked_record_type", "linked_record_id"],
                name="attachment_link_idx",
            ),
        ]

    def __str__(self) -> str:
        return self.original_filename

    @property
    def is_sensitive(self) -> bool:
        return (
            self.visibility == self.Visibility.SENSITIVE
            or self.sensitivity != self.Sensitivity.NORMAL
        )
