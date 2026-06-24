"""atlas selectors — read-only queries (Coding Standards §6, D9)."""
from __future__ import annotations

from django.db.models import Q

from apps.atlas.models import AtlasList, AtlasListItem, AtlasNote, AtlasReminder
from apps.permissions.visibility import apply_visibility


def list_notes(user=None) -> list[AtlasNote]:
    qs = AtlasNote.objects.order_by("-updated_at")
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_note(pk: int) -> AtlasNote | None:
    return AtlasNote.objects.filter(pk=pk).first()


def search_notes(user, query: str) -> list[AtlasNote]:
    """Full-text search over notes title + body (D9).

    Uses icontains for SQLite compatibility in tests. In production the DB is
    Postgres and this can be upgraded to SearchVector + tsvector without
    changing the selector signature.
    """
    qs = AtlasNote.objects.filter(
        Q(title__icontains=query) | Q(body__icontains=query)
    )
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


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
    """Search notes, list titles, and reminders in one call."""
    return {
        "notes": search_notes(user, query),
        "lists": list(AtlasList.objects.filter(
            Q(title__icontains=query)
        )),
        "reminders": list(AtlasReminder.objects.filter(
            Q(title__icontains=query) | Q(body__icontains=query)
        )),
    }
