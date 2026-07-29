"""Global search API — normalized results from enabled, permitted surfaces."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.search import selectors


class GlobalSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        query = (request.query_params.get("q") or "").strip()
        if len(query) < 2:
            return Response({"results": [], "locked_nodes": []})
        return Response(selectors.search_all(request._request, query))
