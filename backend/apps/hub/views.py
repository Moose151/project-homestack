"""hub views — dashboard (GET /hub/, /hub/kiosk/) and widget configuration (M2.5 A.1)."""
from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.hub.selectors import list_widget_config
from apps.hub.serializers import (
    HouseholdWidgetWriteSerializer,
    HubWidgetConfigSerializer,
    UserWidgetOrderWriteSerializer,
    UserWidgetWriteSerializer,
)
from apps.hub.services import (
    HubError,
    get_hub_widgets,
    set_household_widget,
    set_user_widget,
    set_user_widget_order,
)
from apps.accounts.services import is_reauthed
from apps.nodes.access import node_requires_reauth
from apps.permissions.drf import HomeStackPermission

_HubPerm = HomeStackPermission.for_resource("hub")


class HubView(APIView):
    permission_classes = [_HubPerm]

    def get(self, request: Request) -> Response:
        # Two different questions, deliberately not one flag.
        #
        # `session_reauthed` gates the cross-node sensitivity filter (Upcoming excludes
        # financial/health/document/private entries until the reader re-authenticates), so it
        # must stay strictly session-based — a household that turned Money's own prompt off
        # must not thereby publish Health entries to the Dashboard.
        #
        # `solace_unlocked` is the canonical per-node question from apps.nodes.access: a node is
        # open when it does not require re-authentication, or when the session has already
        # re-authenticated. The Dashboard previously used the session answer for both, so with
        # Money's lock switched off its widget stayed locked forever — opening Money could never
        # change it, because nothing was ever asking whether Money was locked at all.
        session_reauthed = is_reauthed(request._request)
        solace_unlocked = not node_requires_reauth("solace") or session_reauthed
        return Response({
            "widgets": get_hub_widgets(
                request.user,
                kiosk_mode=False,
                sensitive_unlocked=session_reauthed,
                solace_unlocked=solace_unlocked,
            )
        })


class KioskHubView(APIView):
    permission_classes = [_HubPerm]

    def get(self, request: Request) -> Response:
        # A kiosk is a shared screen with no session re-authentication: both answers are "no"
        # regardless of how the household configured the node's own lock.
        return Response({"widgets": get_hub_widgets(
            request.user, kiosk_mode=True, sensitive_unlocked=False, solace_unlocked=False,
        )})


class HubWidgetConfigView(APIView):
    """GET the widget catalogue + household/user configuration (drives the config UI)."""

    permission_classes = [_HubPerm]

    def get(self, request: Request) -> Response:
        data = HubWidgetConfigSerializer(list_widget_config(request.user), many=True).data
        return Response({"widgets": data})


class HouseholdWidgetView(APIView):
    """PATCH household-level widget config (enable/disable, order, size). Admin/manager only."""

    permission_classes = [_HubPerm]

    def patch(self, request: Request, key: str) -> Response:
        serializer = HouseholdWidgetWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            set_household_widget(request.user, key, **serializer.validated_data)
        except HubError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"widgets": list_widget_config(request.user)})


class UserWidgetView(APIView):
    """PATCH per-user widget override (hide/show, reorder) on the caller's own Hub."""

    permission_classes = [_HubPerm]
    permission_action = "view"  # arranging your own Hub needs only hub.view

    def patch(self, request: Request, key: str) -> Response:
        serializer = UserWidgetWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            set_user_widget(request.user, key, **serializer.validated_data)
        except HubError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"widgets": list_widget_config(request.user)})


class UserWidgetOrderView(APIView):
    """PATCH the caller's complete widget order in one fast, atomic request."""

    permission_classes = [_HubPerm]
    permission_action = "view"

    def patch(self, request: Request) -> Response:
        serializer = UserWidgetOrderWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            set_user_widget_order(request.user, serializer.validated_data["keys"])
        except HubError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"widgets": list_widget_config(request.user)})
