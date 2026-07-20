"""home_wiki selectors — read-only queries (Coding Standards §6, D9)."""
from __future__ import annotations

from django.db import connection
from django.db.models import Count, Q

from apps.home_wiki.models import WikiCategory, WikiPage
from apps.permissions.visibility import apply_visibility


def _search(qs, query: str, fields: list[str]):
    """Filter ``qs`` by ``query`` across ``fields`` (D9). Postgres FTS in prod, icontains on SQLite."""
    if connection.vendor == "postgresql":
        from django.contrib.postgres.search import SearchQuery, SearchVector
        return qs.annotate(_search=SearchVector(*fields)).filter(_search=SearchQuery(query))
    clause = Q()
    for field in fields:
        clause |= Q(**{f"{field}__icontains": query})
    return qs.filter(clause)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

def list_categories(user=None, *, include_hidden: bool = False):
    qs = WikiCategory.objects.annotate(
        page_count=Count("pages", filter=Q(pages__deleted_at__isnull=True))
    ).order_by("display_order", "name")
    if not include_hidden:
        qs = qs.filter(is_hidden=False)
    return list(qs)


def get_category(pk: int) -> WikiCategory | None:
    return WikiCategory.objects.filter(pk=pk).first()


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def list_pages(
    user=None, *, category_id: int | None = None, favourites_only: bool = False,
    emergency_only: bool = False, kiosk_safe_only: bool = False, limit: int | None = None,
    order_by_updated: bool = False,
):
    qs = WikiPage.objects.select_related("category")
    qs = qs.order_by("-updated_at") if order_by_updated else qs.order_by("-is_favourite", "title")
    if category_id is not None:
        qs = qs.filter(category_id=category_id)
    if favourites_only:
        qs = qs.filter(is_favourite=True)
    if emergency_only:
        qs = qs.filter(is_emergency=True)
    if kiosk_safe_only:
        qs = qs.filter(is_kiosk_safe=True)
    if user is not None:
        qs = apply_visibility(qs, user)
    if limit is not None:
        qs = qs[:limit]
    return list(qs)


def get_page(pk: int) -> WikiPage | None:
    return WikiPage.objects.filter(pk=pk).first()


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search_wiki(user, query: str) -> list[WikiPage]:
    """Permission-filtered FTS across page title, body and tags (D9, Node Spec 12)."""
    qs = _search(WikiPage.objects.select_related("category"), query, ["title", "body", "tags"])
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs.order_by("-is_favourite", "title"))
