"""atlas services — write operations (Coding Standards §6)."""
from __future__ import annotations

from django.utils import timezone

from apps.accounts.models import User
from apps.atlas.models import AtlasList, AtlasListItem, AtlasNote, AtlasReminder
from apps.core.models import get_active_household
from apps.scheduling.helpers import delete_event_for, sync_event_for


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

def create_note(acting_user: User, **data) -> AtlasNote:
    household = get_active_household()
    note = AtlasNote(
        household=household, created_by=acting_user, updated_by=acting_user, **data
    )
    note.save()
    return note


def update_note(acting_user: User, note: AtlasNote, **data) -> AtlasNote:
    allowed = {"title", "body", "visibility", "sensitivity"}
    for key, val in data.items():
        if key in allowed:
            setattr(note, key, val)
    note.updated_by = acting_user
    note.save()
    return note


def delete_note(acting_user: User, note: AtlasNote) -> None:
    note.updated_by = acting_user
    note.save(update_fields=["updated_by", "updated_at"])
    note.soft_delete()


# ---------------------------------------------------------------------------
# Lists
# ---------------------------------------------------------------------------

def create_atlas_list(acting_user: User, **data) -> AtlasList:
    household = get_active_household()
    atlas_list = AtlasList(
        household=household, created_by=acting_user, updated_by=acting_user, **data
    )
    atlas_list.save()
    return atlas_list


def update_atlas_list(acting_user: User, atlas_list: AtlasList, **data) -> AtlasList:
    allowed = {"title", "list_type", "visibility"}
    for key, val in data.items():
        if key in allowed:
            setattr(atlas_list, key, val)
    atlas_list.updated_by = acting_user
    atlas_list.save()
    return atlas_list


def delete_atlas_list(acting_user: User, atlas_list: AtlasList) -> None:
    atlas_list.updated_by = acting_user
    atlas_list.save(update_fields=["updated_by", "updated_at"])
    atlas_list.soft_delete()


# ---------------------------------------------------------------------------
# List items
# ---------------------------------------------------------------------------

def create_list_item(acting_user: User, atlas_list: AtlasList, **data) -> AtlasListItem:
    household = get_active_household()
    item = AtlasListItem(
        household=household,
        atlas_list=atlas_list,
        created_by=acting_user,
        updated_by=acting_user,
        **data,
    )
    item.save()
    return item


def update_list_item(acting_user: User, item: AtlasListItem, **data) -> AtlasListItem:
    allowed = {"title", "notes", "quantity", "position", "due_at", "assigned_to_person_id"}
    for key, val in data.items():
        if key in allowed:
            setattr(item, key, val)
    item.updated_by = acting_user
    item.save()
    return item


def complete_list_item(acting_user: User, item: AtlasListItem) -> AtlasListItem:
    if not item.is_complete:
        item.completed_at = timezone.now()
        item.completed_by = acting_user
        item.updated_by = acting_user
        item.save()
    return item


def uncomplete_list_item(acting_user: User, item: AtlasListItem) -> AtlasListItem:
    if item.is_complete:
        item.completed_at = None
        item.completed_by = None
        item.updated_by = acting_user
        item.save()
    return item


def delete_list_item(acting_user: User, item: AtlasListItem) -> None:
    item.updated_by = acting_user
    item.save(update_fields=["updated_by", "updated_at"])
    item.soft_delete()


# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------

def create_reminder(acting_user: User, **data) -> AtlasReminder:
    household = get_active_household()
    reminder = AtlasReminder(
        household=household, created_by=acting_user, updated_by=acting_user, **data
    )
    reminder.save()
    sync_event_for(reminder)
    return reminder


def update_reminder(acting_user: User, reminder: AtlasReminder, **data) -> AtlasReminder:
    allowed = {"title", "body", "due_at", "is_all_day", "recurrence_rule", "visibility", "sensitivity"}
    for key, val in data.items():
        if key in allowed:
            setattr(reminder, key, val)
    reminder.updated_by = acting_user
    reminder.save()
    sync_event_for(reminder)
    return reminder


def delete_reminder(acting_user: User, reminder: AtlasReminder) -> None:
    delete_event_for(reminder)
    reminder.updated_by = acting_user
    reminder.save(update_fields=["updated_by", "updated_at"])
    reminder.soft_delete()
