"""Event-bus dispatcher — turns other nodes' domain events into notifications
(docs/32_Core_Notifications_and_Push.md §7). Subscribed via NotificationsConfig.ready(),
matching the existing apps.achievements/apps.homestead/apps.solace pattern.

Each handler re-fetches the affected record through a permission-aware queryset and re-checks
`apply_visibility` per candidate recipient — never trusts the thin event payload for anything
permission-relevant. This is what keeps a private list's activity from leaking to a household
member who couldn't already see that list.
"""
from __future__ import annotations

from apps.accounts.models import User
from apps.events.bus import subscribe
from apps.notifications.services import notify_bundled
from apps.permissions.visibility import apply_visibility


def _notify_household_activity(*, actor, record_qs, source_node: str, title: str, message: str, action_url: str) -> None:
    if actor is None:
        return
    for recipient in User.objects.filter(is_active=True, household_id=actor.household_id).exclude(pk=actor.pk):
        if apply_visibility(record_qs, recipient).exists():
            notify_bundled(
                recipient, category="household_activity", source_node=source_node,
                title=title, message=message, action_url=action_url,
            )


def _atlas_tab_for(list_type: str) -> str:
    if list_type == "grocery":
        return "grocery"
    if list_type == "shopping":
        return "shopping"
    return "lists"


def _on_scheduling_event_created(sender, *, payload, **kwargs) -> None:
    from apps.scheduling.models import CalendarEvent

    event = CalendarEvent.all_objects.filter(pk=payload["event_id"]).first()
    if event is None:
        return
    actor = event.created_by
    date_str = event.start_at.date().isoformat() if event.start_at else ""
    _notify_household_activity(
        actor=actor, record_qs=CalendarEvent.objects.filter(pk=event.id), source_node="scheduling",
        title=f"{actor.display_name} added to the calendar" if actor else "Added to the calendar",
        message=event.title,
        action_url=f"/calendar?date={date_str}" if date_str else "/calendar",
    )


def _on_atlas_list_item_created(sender, *, payload, **kwargs) -> None:
    from apps.atlas.models import AtlasList, AtlasListItem

    item = AtlasListItem.all_objects.filter(pk=payload["item_id"]).first()
    if item is None:
        return
    actor = item.created_by
    atlas_list = item.atlas_list
    _notify_household_activity(
        actor=actor, record_qs=AtlasList.objects.filter(pk=atlas_list.id), source_node="atlas",
        title=f"{actor.display_name} added to {atlas_list.title}" if actor else f"Added to {atlas_list.title}",
        message=item.title,
        action_url=f"/atlas?tab={_atlas_tab_for(atlas_list.list_type)}",
    )


def _on_books_entry_finished(sender, *, payload, **kwargs) -> None:
    from apps.books.models import PersonalBookEntry

    entry = PersonalBookEntry.all_objects.filter(pk=payload["entry_id"]).first()
    if entry is None:
        return
    actor = entry.user
    _notify_household_activity(
        actor=actor, record_qs=PersonalBookEntry.objects.filter(pk=entry.id), source_node="books",
        title=f"{actor.display_name} finished a book" if actor else "Finished a book",
        message=entry.book.title,
        action_url="/books",
    )


def connect() -> None:
    subscribe("scheduling.event_created", _on_scheduling_event_created)
    subscribe("atlas.list_item_created", _on_atlas_list_item_created)
    subscribe("books.entry_finished", _on_books_entry_finished)
