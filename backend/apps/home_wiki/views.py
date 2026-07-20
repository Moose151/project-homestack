"""home_wiki views — thin wrappers over selectors/services (Coding Standards §6)."""
from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.home_wiki import selectors, services
from apps.home_wiki.serializers import WikiCategorySerializer, WikiPageSerializer
from apps.permissions.drf import HomeStackPermission

_WikiPerm = HomeStackPermission.for_resource("homewiki")


def _int_param(request: Request, name: str) -> int | None:
    raw = request.query_params.get(name)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class WikiSearchView(APIView):
    permission_classes = [_WikiPerm]

    def get(self, request: Request) -> Response:
        query = (request.query_params.get("q") or "").strip()
        if not query:
            return Response({"pages": []})
        pages = selectors.search_wiki(request.user, query)
        return Response({"pages": WikiPageSerializer(pages, many=True).data})


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

class CategoryListView(APIView):
    permission_classes = [_WikiPerm]

    def get(self, request: Request) -> Response:
        include_hidden = request.query_params.get("hidden") == "1"
        cats = selectors.list_categories(request.user, include_hidden=include_hidden)
        return Response(WikiCategorySerializer(cats, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = WikiCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_category(request.user, **serializer.validated_data)
        return Response(WikiCategorySerializer(obj).data, status=status.HTTP_201_CREATED)


class CategoryDetailView(APIView):
    permission_classes = [_WikiPerm]

    def _get(self, pk: int):
        obj = selectors.get_category(pk)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, category_id: int) -> Response:
        obj = self._get(category_id)
        serializer = WikiCategorySerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_category(request.user, obj, **serializer.validated_data)
        return Response(WikiCategorySerializer(obj).data)

    def delete(self, request: Request, category_id: int) -> Response:
        services.delete_category(request.user, self._get(category_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

class PageListView(APIView):
    permission_classes = [_WikiPerm]

    def get(self, request: Request) -> Response:
        pages = selectors.list_pages(
            request.user,
            category_id=_int_param(request, "category"),
            favourites_only=request.query_params.get("favourites") == "1",
            emergency_only=request.query_params.get("emergency") == "1",
            order_by_updated=request.query_params.get("recent") == "1",
        )
        return Response(WikiPageSerializer(pages, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = WikiPageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_page(request.user, **serializer.validated_data)
        return Response(WikiPageSerializer(obj).data, status=status.HTTP_201_CREATED)


class PageDetailView(APIView):
    permission_classes = [_WikiPerm]

    def _get(self, pk: int):
        obj = selectors.get_page(pk)
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request: Request, page_id: int) -> Response:
        return Response(WikiPageSerializer(self._get(page_id)).data)

    def patch(self, request: Request, page_id: int) -> Response:
        obj = self._get(page_id)
        serializer = WikiPageSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_page(request.user, obj, **serializer.validated_data)
        return Response(WikiPageSerializer(obj).data)

    def delete(self, request: Request, page_id: int) -> Response:
        services.delete_page(request.user, self._get(page_id))
        return Response(status=status.HTTP_204_NO_CONTENT)
