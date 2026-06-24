"""
audit.AuditLog — immutable append-only audit records (Security §13).

Not a HouseholdBaseModel: no soft-delete, no updated_at, no created_by field
(the actor is recorded in `user`). Entries are never modified or deleted.
"""
from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    household = models.ForeignKey(
        "core.Household", on_delete=models.CASCADE, related_name="audit_logs"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    action = models.CharField(max_length=100)
    target_node = models.ForeignKey(
        "nodes.Node", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    target_record_type = models.CharField(max_length=100, blank=True, default="")
    target_record_id = models.PositiveIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    metadata_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        actor = str(self.user) if self.user_id else "system"
        return f"{actor} — {self.action}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("AuditLog entries are immutable.")
        super().save(*args, **kwargs)
