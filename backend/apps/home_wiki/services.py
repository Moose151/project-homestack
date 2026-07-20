"""home_wiki services — write operations (Coding Standards §6)."""
from __future__ import annotations

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.home_wiki import events
from apps.home_wiki.models import WikiCategory, WikiPage

# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

_CATEGORY_FIELDS = {"name", "colour", "icon", "display_order", "is_hidden"}


def create_category(acting_user: User, **data) -> WikiCategory:
    obj = WikiCategory(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    return obj


def update_category(acting_user: User, obj: WikiCategory, **data) -> WikiCategory:
    for key, val in data.items():
        if key in _CATEGORY_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    return obj


def delete_category(acting_user: User, obj: WikiCategory) -> None:
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

_PAGE_FIELDS = {
    "title", "body", "category_id", "tags", "is_favourite", "is_emergency",
    "is_kiosk_safe", "visibility", "sensitivity",
}


def create_page(acting_user: User, **data) -> WikiPage:
    obj = WikiPage(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    obj.save()
    events.page_created(obj.id, obj.household_id)
    return obj


def update_page(acting_user: User, obj: WikiPage, **data) -> WikiPage:
    was_emergency = obj.is_emergency
    for key, val in data.items():
        if key in _PAGE_FIELDS:
            setattr(obj, key, val)
    obj.updated_by = acting_user
    obj.save()
    events.page_updated(obj.id, obj.household_id)
    if obj.is_emergency and not was_emergency:
        events.emergency_page_updated(obj.id, obj.household_id)
    return obj


def delete_page(acting_user: User, obj: WikiPage) -> None:
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()
    events.page_deleted(obj.id, obj.household_id)
