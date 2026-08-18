"""Quick Launch — one person's shortcuts to the places they actually go.

Distinct from the two navigation systems that already exist (docs/39 §2): the desktop sidebar
and the configurable mobile dock are *navigation* — broad, node-level, and largely the same for
everyone. A Quick Launch shortcut is personal and may point deeper than a node root: "Groceries"
is one particular list, "Kitchen" is one particular room.

Why a model rather than the generic UserPreference JSON store: that store's own contract is that
its values are ordering hints and "never authority", and its validators accept only capped lists
of slugs. A shortcut carries a referenced object id, a user-authored label, a launch mode and a
UUID that appears in a URL and must be authorised per user. That is relational data behind an
authorisation boundary, so it gets a row.
"""
from __future__ import annotations

import uuid

from django.db import models

from apps.core.models import AllObjectsManager, HouseholdBaseModel, HouseholdManager


class QuickLaunchShortcut(HouseholdBaseModel):
    """One shortcut belonging to exactly one login.

    The shortcut stores *intent*, never a route. ``target_key`` names an entry in the registry
    (apps/quicklaunch/registry.py) and ``target_object_id`` optionally names the record within
    it. The destination URL is resolved at launch time, so internal routes can change without
    breaking a saved or shared shortcut — and a user cannot smuggle an arbitrary path or an
    external URL into one, because no field here can hold either.
    """

    class LaunchMode(models.TextChoices):
        NORMAL = "normal", "Normal"
        # Reserved contract, honoured by the client where it makes sense (docs/39 §7).
        FOCUSED = "focused", "Focused"

    # Public identifier. Non-sequential so one cannot be guessed by counting, though guessing is
    # not the boundary — every launch re-checks ownership regardless.
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="quick_launch_shortcuts",
    )
    target_key = models.CharField(max_length=64)
    # Only meaningful for targets whose registry entry requires an object.
    target_object_id = models.PositiveBigIntegerField(null=True, blank=True)
    custom_label = models.CharField(max_length=60, blank=True, default="")
    display_order = models.PositiveSmallIntegerField(default=0)
    launch_mode = models.CharField(
        max_length=10, choices=LaunchMode.choices, default=LaunchMode.NORMAL,
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "quick launch shortcut"
        verbose_name_plural = "quick launch shortcuts"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "target_key", "target_object_id"],
                condition=models.Q(deleted_at__isnull=True),
                name="quicklaunch_unique_active_shortcut",
            ),
        ]

    def __str__(self) -> str:
        return self.custom_label or self.target_key
