"""Write operations on a person's own Quick Launch shortcuts.

Every function takes the acting user and scopes to *their* rows. There is no service here that
can reach another person's shortcut: the queryset is filtered by user before anything else, so
a mistaken or forged identifier produces "not found" rather than someone else's data.
"""
from __future__ import annotations

from django.db import transaction

from apps.core.models import get_active_household
from apps.quicklaunch.models import QuickLaunchShortcut
from apps.quicklaunch.registry import validate_selection

MAX_SHORTCUTS = 20


class QuickLaunchError(Exception):
    """A domain error safe to show the household."""


def shortcuts_for(user):
    return QuickLaunchShortcut.objects.filter(user=user)


def get_own_shortcut(user, public_id):
    """One of this user's shortcuts, or None.

    Ownership is part of the lookup rather than a check afterwards — that is what makes an
    altered identifier in a launch URL indistinguishable from one that never existed.
    """
    return QuickLaunchShortcut.objects.filter(user=user, public_id=public_id).first()


@transaction.atomic
def create_shortcut(user, *, target_key, target_object_id=None, custom_label="",
                    launch_mode=QuickLaunchShortcut.LaunchMode.NORMAL):
    target = validate_selection(target_key, target_object_id, user)
    if launch_mode not in target.launch_modes:
        launch_mode = QuickLaunchShortcut.LaunchMode.NORMAL

    existing = shortcuts_for(user)
    if existing.count() >= MAX_SHORTCUTS:
        raise QuickLaunchError(f"You can keep up to {MAX_SHORTCUTS} shortcuts.")
    if existing.filter(target_key=target_key, target_object_id=target_object_id).exists():
        raise QuickLaunchError("That shortcut is already in your Quick Launch.")

    highest = existing.order_by("-display_order").values_list("display_order", flat=True).first()
    shortcut = QuickLaunchShortcut(
        household=get_active_household(),
        created_by=user,
        updated_by=user,
        user=user,
        target_key=target_key,
        target_object_id=target_object_id,
        custom_label=(custom_label or "").strip()[:60],
        launch_mode=launch_mode,
        display_order=(highest + 1) if highest is not None else 0,
    )
    shortcut.save()
    return shortcut


def update_shortcut(user, shortcut, *, custom_label=None, launch_mode=None):
    """Rename or change the launch mode. The destination itself is immutable.

    Re-pointing a shortcut at a different record would let one row quietly become a different
    thing; removing and adding is clearer and costs the user nothing.
    """
    if custom_label is not None:
        shortcut.custom_label = custom_label.strip()[:60]
    if launch_mode is not None:
        from apps.quicklaunch.registry import REGISTRY
        target = REGISTRY.get(shortcut.target_key)
        if target and launch_mode in target.launch_modes:
            shortcut.launch_mode = launch_mode
    shortcut.updated_by = user
    shortcut.save()
    return shortcut


def delete_shortcut(user, shortcut) -> None:
    shortcut.updated_by = user
    shortcut.save(update_fields=["updated_by", "updated_at"])
    shortcut.soft_delete()


@transaction.atomic
def reorder_shortcuts(user, public_ids) -> list:
    """Apply a new order. Ids that are not this user's are ignored, never applied."""
    owned = {str(row.public_id): row for row in shortcuts_for(user)}
    order = 0
    for public_id in public_ids:
        row = owned.pop(str(public_id), None)
        if row is None:
            continue
        row.display_order = order
        row.updated_by = user
        row.save(update_fields=["display_order", "updated_by", "updated_at"])
        order += 1
    # Anything the client did not mention keeps its relative order after the named ones.
    for row in sorted(owned.values(), key=lambda item: (item.display_order, item.id)):
        row.display_order = order
        row.save(update_fields=["display_order", "updated_at"])
        order += 1
    return list(shortcuts_for(user))
