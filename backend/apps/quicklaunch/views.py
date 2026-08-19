"""Quick Launch API.

Everything here is scoped to `request.user` before anything else happens. There is no endpoint
that takes a household-wide or admin view of shortcuts, because a shortcut is personal — so the
"can this person touch this row" question is answered by the lookup itself rather than by a
permission check that could be forgotten on one branch.
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.quicklaunch import services
from apps.quicklaunch.serializers import (
    QuickLaunchReorderSerializer,
    QuickLaunchShortcutSerializer,
    QuickLaunchShortcutUpdateSerializer,
    QuickLaunchShortcutWriteSerializer,
)


class _OwnShortcutsMixin:
    # Arranging your own shortcuts needs a login and nothing more: the shortcut grants no
    # access, and every destination re-checks its own permissions at launch.
    permission_classes = [IsAuthenticated]

    def _context(self, request):
        return {"user": request.user, "request_obj": request._request}

    def _serialize(self, request, rows):
        return QuickLaunchShortcutSerializer(
            rows, many=True, context=self._context(request),
        ).data


class ShortcutListView(_OwnShortcutsMixin, APIView):
    def get(self, request: Request) -> Response:
        return Response(self._serialize(request, services.shortcuts_for(request.user)))

    def post(self, request: Request) -> Response:
        serializer = QuickLaunchShortcutWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            shortcut = services.create_shortcut(request.user, **serializer.validated_data)
        except services.QuickLaunchError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            QuickLaunchShortcutSerializer(shortcut, context=self._context(request)).data,
            status=status.HTTP_201_CREATED,
        )


class ShortcutDetailView(_OwnShortcutsMixin, APIView):
    def patch(self, request: Request, public_id) -> Response:
        shortcut = services.get_own_shortcut(request.user, public_id)
        if shortcut is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = QuickLaunchShortcutUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shortcut = services.update_shortcut(request.user, shortcut, **serializer.validated_data)
        return Response(
            QuickLaunchShortcutSerializer(shortcut, context=self._context(request)).data,
        )

    def delete(self, request: Request, public_id) -> Response:
        shortcut = services.get_own_shortcut(request.user, public_id)
        if shortcut is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        services.delete_shortcut(request.user, shortcut)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ShortcutReorderView(_OwnShortcutsMixin, APIView):
    def patch(self, request: Request) -> Response:
        serializer = QuickLaunchReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rows = services.reorder_shortcuts(request.user, serializer.validated_data["ids"])
        return Response(self._serialize(request, rows))


class ShortcutResolveView(_OwnShortcutsMixin, APIView):
    """Turn a shortcut into a destination, now, for this user.

    This is the launch contract (docs/39 §6). The route is produced here rather than stored, so
    a saved shortcut survives internal route changes — and a shortcut whose node was disabled,
    whose permission was withdrawn or whose record was deleted resolves to "unavailable" instead
    of a stale path. A sensitive destination resolves to "locked" until the household's re-auth
    prompt has been satisfied; the client sends the user through the normal unlock and returns
    here afterwards, so the intended destination is preserved.
    """

    def get(self, request: Request, public_id) -> Response:
        from apps.quicklaunch.registry import resolve

        shortcut = services.get_own_shortcut(request.user, public_id)
        if shortcut is None:
            # Someone else's identifier and a nonexistent one answer identically on purpose.
            return Response(
                {"status": "unavailable", "reason": "This shortcut is no longer available."},
                status=status.HTTP_404_NOT_FOUND,
            )
        resolution = resolve(shortcut, request.user, request._request)
        payload = {
            "status": resolution.status,
            "label": resolution.label,
            "reason": resolution.reason,
            "node_key": resolution.node_key,
            "launch_mode": shortcut.launch_mode,
        }
        # The route is only ever handed over when the destination is genuinely open.
        if resolution.status in ("ok", "locked"):
            payload["route"] = resolution.route
        return Response(payload)


class TargetCatalogueView(_OwnShortcutsMixin, APIView):
    """What this user may add. Unavailable destinations are simply absent."""

    def get(self, request: Request) -> Response:
        from apps.quicklaunch.registry import catalogue
        return Response({"targets": catalogue(request.user)})
