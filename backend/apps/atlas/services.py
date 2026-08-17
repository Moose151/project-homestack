"""atlas services — write operations (Coding Standards §6)."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.atlas import events
from apps.atlas.models import AtlasContact, AtlasList, AtlasListItem, AtlasListSuggestion, AtlasNote, AtlasReminder
from apps.core.assignment import apply_assignees, pop_assignees
from apps.core.models import get_active_household
from apps.people.selectors import person_for_user
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
    owner = data.get("owner_person")
    if owner and acting_user.role not in {User.Role.ADMIN, User.Role.MANAGER}:
        if owner.linked_user_id != acting_user.id:
            raise PermissionError("You can only create a personal list in your own Corner.")
    household = get_active_household()
    atlas_list = AtlasList(
        household=household, created_by=acting_user, updated_by=acting_user, **data
    )
    atlas_list.save()
    return atlas_list


def update_atlas_list(acting_user: User, atlas_list: AtlasList, **data) -> AtlasList:
    requested_owner = data.get("owner_person")
    if requested_owner and acting_user.role not in {User.Role.ADMIN, User.Role.MANAGER}:
        if requested_owner.linked_user_id != acting_user.id:
            raise PermissionError("You can only place a personal list in your own Corner.")
    allowed = {"title", "list_type", "visibility", "owner_person"}
    for key, val in data.items():
        if key in allowed:
            setattr(atlas_list, key, val)
    atlas_list.updated_by = acting_user
    atlas_list.save()
    return atlas_list


def can_manage_personal_list(acting_user: User, atlas_list: AtlasList) -> bool:
    """Personal lists are edited by their owner; managers retain household oversight."""
    return atlas_list.owner_person_id is None or acting_user.role in {
        User.Role.ADMIN, User.Role.MANAGER,
    } or atlas_list.owner_person.linked_user_id == acting_user.id


def delete_atlas_list(acting_user: User, atlas_list: AtlasList) -> None:
    for item in atlas_list.items.all():
        delete_event_for(item)
    atlas_list.updated_by = acting_user
    atlas_list.save(update_fields=["updated_by", "updated_at"])
    atlas_list.soft_delete()


# ---------------------------------------------------------------------------
# List items
# ---------------------------------------------------------------------------

def create_list_item(acting_user: User, atlas_list: AtlasList, **data) -> AtlasListItem:
    people = pop_assignees(data)
    cache_image = data.pop("cache_image", None)
    watch_enabled = data.pop("price_watch_enabled", None)
    if cache_image is None:
        cache_image = bool(data.get("source_image_url"))
    if watch_enabled is None:
        watch_enabled = atlas_list.list_type == AtlasList.ListType.WISHLIST and bool(data.get("product_url"))
    if data.get("product_url"):
        data["imported_at"] = timezone.now()
    household = get_active_household()
    item = AtlasListItem(
        household=household,
        atlas_list=atlas_list,
        created_by=acting_user,
        updated_by=acting_user,
        **data,
    )
    item.save()
    apply_assignees(item, people)
    sync_event_for(item)
    _finish_product_item(acting_user, item, cache_image=cache_image, watch_enabled=watch_enabled)
    events.list_item_created(item.id, household.id)
    return item


def update_list_item(acting_user: User, item: AtlasListItem, **data) -> AtlasListItem:
    people = pop_assignees(data)
    cache_image = data.pop("cache_image", False)
    watch_enabled = data.pop("price_watch_enabled", None)
    allowed = {
        "title", "notes", "quantity", "priority", "position", "due_at", "product_url",
        "source_image_url", "retailer", "unit_price", "currency",
    }
    for key, val in data.items():
        if key in allowed:
            setattr(item, key, val)
    item.updated_by = acting_user
    item.save()
    apply_assignees(item, people)
    sync_event_for(item)
    _finish_product_item(acting_user, item, cache_image=cache_image, watch_enabled=watch_enabled)
    return item


def _finish_product_item(acting_user: User, item: AtlasListItem, *, cache_image: bool, watch_enabled) -> None:
    if cache_image and item.source_image_url:
        from apps.attachments.services import delete_attachment
        from apps.link_imports.fetch import LinkFetchError
        from apps.link_imports.services import cache_remote_image
        try:
            previous_attachment = item.image_attachment
            item.image_attachment = cache_remote_image(
                acting_user=acting_user, image_url=item.source_image_url, source_node="atlas",
                record_type="AtlasListItem", record_id=item.id,
                visibility=item.atlas_list.visibility,
            )
            item.save(update_fields=["image_attachment", "updated_at"])
            if previous_attachment and previous_attachment.id != item.image_attachment_id:
                delete_attachment(previous_attachment, acting_user=acting_user)
        except LinkFetchError:
            pass
    if watch_enabled is not None and item.product_url and item.unit_price is not None:
        owner = item.atlas_list.owner_person or person_for_user(acting_user)
        if owner:
            from apps.link_imports.services import sync_watch
            sync_watch(
                acting_user=acting_user, owner_person=owner, source_node="atlas",
                record_type="AtlasListItem", record_id=item.id, url=item.product_url,
                title=item.title, retailer=item.retailer, currency=item.currency,
                price=item.unit_price, enabled=watch_enabled,
            )


def complete_list_item(acting_user: User, item: AtlasListItem) -> AtlasListItem:
    if not item.is_complete:
        item.completed_at = timezone.now()
        item.completed_by = acting_user
        item.updated_by = acting_user
        item.save()
        sync_event_for(item)
    return item


def uncomplete_list_item(acting_user: User, item: AtlasListItem) -> AtlasListItem:
    if item.is_complete:
        item.completed_at = None
        item.completed_by = None
        item.updated_by = acting_user
        item.save()
        sync_event_for(item)
    return item


def delete_list_item(acting_user: User, item: AtlasListItem) -> None:
    from apps.attachments.services import delete_attachment
    from apps.link_imports.models import LinkWatch

    delete_event_for(item)
    LinkWatch.objects.filter(
        source_node="atlas", source_record_type="AtlasListItem", source_record_id=item.id,
    ).update(is_active=False, updated_by=acting_user)
    if item.image_attachment:
        delete_attachment(item.image_attachment, acting_user=acting_user)
    item.updated_by = acting_user
    item.save(update_fields=["updated_by", "updated_at"])
    item.soft_delete()


def create_contact(acting_user: User, **data) -> AtlasContact:
    return AtlasContact.objects.create(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )


def update_contact(acting_user: User, contact: AtlasContact, **data) -> AtlasContact:
    for field in {"name", "date_of_birth", "relationship", "notes", "linked_person", "visibility"}:
        if field in data:
            setattr(contact, field, data[field])
    contact.updated_by = acting_user
    contact.save()
    return contact


def delete_contact(acting_user: User, contact: AtlasContact) -> None:
    contact.updated_by = acting_user
    contact.save(update_fields=["updated_by", "updated_at"])
    contact.soft_delete()


def create_list_suggestion(acting_user: User, atlas_list: AtlasList, **data) -> AtlasListSuggestion:
    person = person_for_user(acting_user)
    if person is None:
        raise ValueError("Your login must be linked to a household member to suggest an item.")
    if atlas_list.owner_person_id is None:
        raise ValueError("Suggestions are available on personal lists.")
    suggestion = AtlasListSuggestion.objects.create(
        household=get_active_household(), atlas_list=atlas_list, suggested_by_person=person,
        created_by=acting_user, updated_by=acting_user, **data,
    )
    if atlas_list.owner_person_id != person.id:
        from apps.notifications.services import notify_person
        notify_person(
            atlas_list.owner_person, title=f"{person.name} suggested {suggestion.title}",
            message=f"Review the suggestion for {atlas_list.title}.", source_node="atlas",
            action_url=f"/corners/{atlas_list.owner_person_id}?tab=lists",
            category="corners",
        )
    return suggestion


def _can_review_suggestion(acting_user: User, suggestion: AtlasListSuggestion) -> bool:
    return acting_user.role in {User.Role.ADMIN, User.Role.MANAGER} or (
        suggestion.atlas_list.owner_person_id
        and suggestion.atlas_list.owner_person.linked_user_id == acting_user.id
    )


@transaction.atomic
def accept_list_suggestion(acting_user: User, suggestion: AtlasListSuggestion) -> AtlasListSuggestion:
    if not _can_review_suggestion(acting_user, suggestion):
        raise PermissionError("Only the list owner or a household manager can accept this suggestion.")
    if suggestion.status != AtlasListSuggestion.Status.PENDING:
        return suggestion
    item = create_list_item(
        acting_user, suggestion.atlas_list, title=suggestion.title, notes=suggestion.notes,
        product_url=suggestion.product_url, source_image_url=suggestion.source_image_url,
        retailer=suggestion.retailer, unit_price=suggestion.unit_price, currency=suggestion.currency,
        assigned_to_people=[suggestion.atlas_list.owner_person_id], cache_image=True,
        price_watch_enabled=suggestion.atlas_list.list_type == AtlasList.ListType.WISHLIST,
    )
    suggestion.status = AtlasListSuggestion.Status.ACCEPTED
    suggestion.accepted_item = item
    suggestion.reviewed_by = acting_user
    suggestion.reviewed_at = timezone.now()
    suggestion.updated_by = acting_user
    suggestion.save()
    return suggestion


def dismiss_list_suggestion(acting_user: User, suggestion: AtlasListSuggestion) -> AtlasListSuggestion:
    if not _can_review_suggestion(acting_user, suggestion):
        raise PermissionError("Only the list owner or a household manager can dismiss this suggestion.")
    if suggestion.status == AtlasListSuggestion.Status.PENDING:
        suggestion.status = AtlasListSuggestion.Status.DISMISSED
        suggestion.reviewed_by = acting_user
        suggestion.reviewed_at = timezone.now()
        suggestion.updated_by = acting_user
        suggestion.save()
    return suggestion


# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------

def create_reminder(acting_user: User, **data) -> AtlasReminder:
    people = pop_assignees(data)
    household = get_active_household()
    reminder = AtlasReminder(
        household=household, created_by=acting_user, updated_by=acting_user, **data
    )
    reminder.save()
    apply_assignees(reminder, people)
    sync_event_for(reminder)
    return reminder


def update_reminder(acting_user: User, reminder: AtlasReminder, **data) -> AtlasReminder:
    people = pop_assignees(data)
    allowed = {"title", "body", "due_at", "is_all_day", "recurrence_rule", "visibility", "sensitivity", "notifications_enabled"}
    for key, val in data.items():
        if key in allowed:
            setattr(reminder, key, val)
    reminder.updated_by = acting_user
    reminder.save()
    apply_assignees(reminder, people)
    sync_event_for(reminder)
    return reminder


def delete_reminder(acting_user: User, reminder: AtlasReminder) -> None:
    delete_event_for(reminder)
    reminder.updated_by = acting_user
    reminder.save(update_fields=["updated_by", "updated_at"])
    reminder.soft_delete()
