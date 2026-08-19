"""atlas selectors — read-only queries (Coding Standards §6, D9)."""
from __future__ import annotations

from django.db import connection
from django.db.models import Q

from apps.atlas.models import AtlasContact, AtlasList, AtlasListItem, AtlasListSuggestion, AtlasNote, AtlasReminder
from apps.permissions.visibility import apply_visibility


def _search(qs, query: str, fields: list[str]):
    """Filter ``qs`` by ``query`` across ``fields`` (D9).

    Uses Postgres full-text search (``SearchVector``/``SearchQuery``) in production;
    falls back to ``icontains`` on SQLite (tests). Same selector signature either way.
    """
    if connection.vendor == "postgresql":
        from django.contrib.postgres.search import SearchQuery, SearchVector
        return qs.annotate(_search=SearchVector(*fields)).filter(_search=SearchQuery(query))
    clause = Q()
    for field in fields:
        clause |= Q(**{f"{field}__icontains": query})
    return qs.filter(clause)


def list_notes(user=None) -> list[AtlasNote]:
    qs = AtlasNote.objects.order_by("-updated_at")
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_note(pk: int) -> AtlasNote | None:
    return AtlasNote.objects.filter(pk=pk).first()


def search_notes(user, query: str) -> list[AtlasNote]:
    """Full-text search over note title + body, permission-filtered (D9)."""
    qs = _search(AtlasNote.objects.all(), query, ["title", "body"])
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs.order_by("-updated_at"))


def list_atlas_lists(user=None) -> list[AtlasList]:
    qs = AtlasList.objects.order_by("-updated_at")
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_atlas_list(pk: int, user=None) -> AtlasList | None:
    qs = AtlasList.objects.filter(pk=pk)
    if user is not None:
        qs = apply_visibility(qs, user)
    return qs.first()


def list_items_for_list(atlas_list: AtlasList, *, include_complete: bool = True) -> list[AtlasListItem]:
    qs = AtlasListItem.objects.select_related("atlas_list").filter(atlas_list=atlas_list).order_by("position", "id")
    if not include_complete:
        qs = qs.filter(completed_at__isnull=True)
    return list(qs)


def list_open_items(user=None, *, limit: int | None = None) -> list[AtlasListItem]:
    """Open To-do items the user may see, restricted by the parent list visibility.

    Only ``list_type='todo'`` items are to-dos (D19) — grocery/checklist/general items are
    a different concept and must never leak into a To-do widget/view. Use
    :func:`list_grocery_items` for grocery.
    """
    qs = (
        AtlasListItem.objects.select_related("atlas_list")
        .filter(completed_at__isnull=True, atlas_list__list_type="todo")
        .order_by("atlas_list__title", "position", "id")
    )
    if user is not None:
        visible_list_ids = apply_visibility(AtlasList.objects.all(), user).values_list("id", flat=True)
        qs = qs.filter(atlas_list_id__in=visible_list_ids)
    if limit is not None:
        qs = qs[:limit]
    return list(qs)


def list_today_items(user=None, *, limit: int | None = None) -> list[AtlasListItem]:
    """Overdue and due-today To-do items across Household + all personal lists (D19 §G)."""
    from django.utils import timezone

    end_of_today = timezone.localtime().replace(hour=23, minute=59, second=59, microsecond=999999)
    qs = (
        AtlasListItem.objects.select_related("atlas_list")
        .filter(
            completed_at__isnull=True, atlas_list__list_type="todo",
            due_at__isnull=False, due_at__lte=end_of_today,
        )
        .order_by("due_at", "atlas_list__title", "position", "id")
    )
    if user is not None:
        visible_list_ids = apply_visibility(AtlasList.objects.all(), user).values_list("id", flat=True)
        qs = qs.filter(atlas_list_id__in=visible_list_ids)
    if limit is not None:
        qs = qs[:limit]
    return list(qs)


def list_grocery_items(user=None, *, include_complete: bool = True) -> list[AtlasListItem]:
    """Items on the household's single Grocery list (D19 §C)."""
    qs = (
        AtlasListItem.objects.select_related("atlas_list")
        .filter(atlas_list__list_type="grocery")
        .order_by("atlas_list_id", "position", "id")
    )
    if not include_complete:
        qs = qs.filter(completed_at__isnull=True)
    if user is not None:
        visible_list_ids = apply_visibility(AtlasList.objects.all(), user).values_list("id", flat=True)
        qs = qs.filter(atlas_list_id__in=visible_list_ids)
    return list(qs)


def frequent_grocery_titles(grocery_list: AtlasList, *, limit: int = 6) -> list[str]:
    """Most commonly bought item titles on this list, most-frequent first (D19 §C).

    Looks at completed (bought) items regardless of current state — a household that always
    buys milk should see "Milk" suggested even right after clearing it off the list.
    """
    from collections import Counter

    counts: Counter[str] = Counter()
    display: dict[str, str] = {}
    active_titles = {
        item.title.strip().casefold()
        for item in grocery_list.items.filter(completed_at__isnull=True)
    }
    for title in grocery_list.items.filter(completed_at__isnull=False).values_list("title", flat=True):
        key = title.strip().casefold()
        if not key or key in active_titles:
            continue
        counts[key] += 1
        display.setdefault(key, title.strip())
    ranked = sorted(counts.items(), key=lambda pair: (-pair[1], display[pair[0]]))
    return [display[key] for key, _count in ranked[:limit]]


def list_todo_lists(user=None) -> list[AtlasList]:
    """The Household To-do list plus every personal To-do list (D19 §D)."""
    qs = AtlasList.objects.filter(list_type="todo").order_by("owner_person_id", "title")
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_list_item(pk: int) -> AtlasListItem | None:
    return AtlasListItem.objects.filter(pk=pk).first()


def list_suggestions(atlas_list: AtlasList) -> list[AtlasListSuggestion]:
    return list(atlas_list.suggestions.select_related("suggested_by_person").all())


def get_suggestion(atlas_list: AtlasList, suggestion_id: int) -> AtlasListSuggestion | None:
    return atlas_list.suggestions.select_related("suggested_by_person", "atlas_list__owner_person").filter(pk=suggestion_id).first()


def list_reminders(user=None, *, upcoming_only: bool = False) -> list[AtlasReminder]:
    qs = AtlasReminder.objects.order_by("due_at", "-updated_at")
    if upcoming_only:
        from django.utils import timezone
        qs = qs.filter(due_at__gte=timezone.now())
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_reminder(pk: int) -> AtlasReminder | None:
    return AtlasReminder.objects.filter(pk=pk).first()


def list_contacts(user=None) -> list[AtlasContact]:
    qs = AtlasContact.objects.select_related("linked_person").order_by("name")
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_contact(pk: int, user=None) -> AtlasContact | None:
    qs = AtlasContact.objects.filter(pk=pk)
    if user is not None:
        qs = apply_visibility(qs, user)
    return qs.first()


def search_atlas(user, query: str) -> dict:
    """Search notes, lists, list items and reminders in one call — permission-filtered (D9).

    Notes and reminders carry their own ``visibility``; list items have none, so they are
    restricted to lists the user may see (no leaking items from private/restricted lists).
    """
    lists_qs = _search(AtlasList.objects.all(), query, ["title"])
    reminders_qs = _search(AtlasReminder.objects.all(), query, ["title", "body"])
    items_qs = _search(AtlasListItem.objects.select_related("atlas_list"), query, ["title", "notes"])

    if user is not None:
        lists_qs = apply_visibility(lists_qs, user)
        reminders_qs = apply_visibility(reminders_qs, user)
        visible_list_ids = list(
            apply_visibility(AtlasList.objects.all(), user).values_list("id", flat=True)
        )
        items_qs = items_qs.filter(atlas_list_id__in=visible_list_ids)

    return {
        "notes": search_notes(user, query),
        "lists": list(lists_qs.order_by("-updated_at")),
        "items": list(items_qs.order_by("position", "id")),
        "reminders": list(reminders_qs.order_by("due_at", "-updated_at")),
    }
