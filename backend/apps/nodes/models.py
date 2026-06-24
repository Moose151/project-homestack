"""
nodes models — node registry and per-household configuration (DB design §4).

Node    — global catalogue of all available node types (atlas, pets, etc.).
HouseholdNode — per-household enabled/disabled state + display config.
NodeSetting   — per-household key-value settings for a node.

These are configuration tables, not user content, so they do not inherit
HouseholdBaseModel (no soft-delete, no created_by/updated_by needed here —
changes are captured by audit_logs instead).
"""
from django.db import models


class Node(models.Model):
    """Global catalogue of node types. Seeded by migration; one row per node type."""

    key = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    icon = models.CharField(max_length=100, blank=True, default="")
    is_core = models.BooleanField(default=False)
    is_enabled_by_default = models.BooleanField(default=False)
    requires_setup = models.BooleanField(default=False)
    supports_kiosk = models.BooleanField(default=True)
    supports_sensitive_lock = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self) -> str:
        return self.name or self.key


class HouseholdNode(models.Model):
    """Per-household enable/display state for a node."""

    household = models.ForeignKey(
        "core.Household", on_delete=models.CASCADE, related_name="household_nodes"
    )
    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="household_configs")
    is_enabled = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)
    requires_reauthentication = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0)
    custom_name = models.CharField(max_length=100, blank=True, default="")
    custom_icon = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("household", "node")]
        ordering = ["display_order", "node__key"]

    def __str__(self) -> str:
        state = "enabled" if self.is_enabled else "disabled"
        return f"{self.node.key} ({state})"


class NodeSetting(models.Model):
    """Per-household key-value settings for a node."""

    household = models.ForeignKey(
        "core.Household", on_delete=models.CASCADE, related_name="node_settings"
    )
    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="settings")
    key = models.CharField(max_length=100)
    value_json = models.JSONField(null=True, blank=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("household", "node", "key")]

    def __str__(self) -> str:
        return f"{self.node.key}.{self.key}"
