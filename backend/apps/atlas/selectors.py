"""atlas selectors — read-only queries (Coding Standards §6, D9)."""
from __future__ import annotations

from django.db import connection
from django.db.models import Q

from apps.atlas.models import AtlasList, AtlasListItem, AtlasNote, AtlasReminder
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


def get_atlas_list(pk: int) -> AtlasList | None:
    return AtlasList.objects.filter(pk=pk).first()


def list_items_for_list(atlas_list: AtlasList, *, include_complete: bool = True) -> list[AtlasListItem]:
    qs = AtlasListItem.objects.filter(atlas_list=atlas_list).order_by("position", "id")
    if not include_complete:
        qs = qs.filter(completed_at__isnull=True)
    return list(qs)


def list_open_items(user=None, *, limit: int | None = None) -> list[AtlasListItem]:
    """Open list items the user may see, restricted by the parent list visibility."""
    qs = AtlasListItem.objects.filter(completed_at__isnull=True).order_by("atlas_list__title", "position", "id")
    if user is not None:
        visible_list_ids = apply_visibility(AtlasList.objects.all(), user).values_list("id", flat=True)
        qs = qs.filter(atlas_list_id__in=visible_list_ids)
    if limit is not None:
        qs = qs[:limit]
    return list(qs)


def get_list_item(pk: int) -> AtlasListItem | None:
    return AtlasListItem.objects.filter(pk=pk).first()


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


def search_atlas(user, query: str) -> dict:
    """Search notes, lists, list items and reminders in one call — permission-filtered (D9).

    Notes and reminders carry their own ``visibility``; list items have none, so they are
    restricted to lists the user may see (no leaking items from private/restricted lists).
    """
    lists_qs = _search(AtlasList.objects.all(), query, ["title"])
    reminders_qs = _search(AtlasReminder.objects.all(), query, ["title", "body"])
    items_qs = _search(AtlasListItem.objects.all(), query, ["title", "notes"])

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
