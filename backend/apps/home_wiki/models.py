"""home_wiki models — the household knowledge base (Node Spec 12).

Milestone 3 V1 slice: persistent reference pages the household looks up repeatedly — WiFi,
bin night, emergency contacts, appliance/how-to procedures. Distinct from Atlas (temporary
notes/lists) and Documents (secure files): Home Wiki owns long-lived, searchable pages.

Models inherit HouseholdBaseModel (household scoping, audit fields, soft-delete). Visibility +
sensitivity feed the central resolver's `apply_visibility` (D10); `is_kiosk_safe` gates the
kiosk/child read view separately. V1 keeps the body as plain/basic text; Markdown, templates,
linked pages and page history are parked (Node Spec 16/18).
"""
from __future__ import annotations

from django.db import models

from apps.core.models import AllObjectsManager, HouseholdBaseModel, HouseholdManager


class Visibility(models.TextChoices):
    PRIVATE = "private", "Private"
    HOUSEHOLD = "household", "Household"
    ROLE_RESTRICTED = "role_restricted", "Role Restricted"
    SENSITIVE = "sensitive", "Sensitive"


class Sensitivity(models.TextChoices):
    NORMAL = "normal", "Normal"
    SENSITIVE = "sensitive", "Sensitive"


class WikiCategory(HouseholdBaseModel):
    """A grouping for wiki pages (Emergency, Utilities, Appliances, …). Admin-manageable."""

    name = models.CharField(max_length=120)
    colour = models.CharField(max_length=20, blank=True, default="")
    icon = models.CharField(max_length=40, blank=True, default="")
    display_order = models.PositiveSmallIntegerField(default=0)
    is_hidden = models.BooleanField(default=False)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "wiki category"
        verbose_name_plural = "wiki categories"
        ordering = ["display_order", "name"]

    def __str__(self) -> str:
        return self.name


class WikiPage(HouseholdBaseModel):
    """A single knowledge-base page: title + body, categorised, tagged, permissioned."""

    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")
    category = models.ForeignKey(
        WikiCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pages",
    )
    tags = models.CharField(
        max_length=500, blank=True, default="",
        help_text="Comma-separated tags; exposed as a list in the API.",
    )
    is_favourite = models.BooleanField(default=False)  # pinned to the top of Wiki/Hub/kiosk
    is_emergency = models.BooleanField(default=False)  # surfaced in the emergency-info area
    is_kiosk_safe = models.BooleanField(default=False)  # readable on kiosk / by children
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )
    sensitivity = models.CharField(
        max_length=20, choices=Sensitivity.choices, default=Sensitivity.NORMAL
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "wiki page"
        ordering = ["-is_favourite", "title"]

    def __str__(self) -> str:
        return self.title

    @property
    def tag_list(self) -> list[str]:
        return [t.strip() for t in self.tags.split(",") if t.strip()]
