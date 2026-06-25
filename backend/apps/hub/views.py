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
    UserWidgetWriteSerializer,
)
from apps.hub.services import HubError, get_hub_widgets, set_household_widget, set_user_widget
from apps.permissions.drf import HomeStackPermission

_HubPerm = HomeStackPermission.for_resource("hub")


class HubView(APIView):
    permission_classes = [_HubPerm]

    def get(self, request: Request) -> Response:
        return Response({"widgets": get_hub_widgets(request.user, kiosk_mode=False)})


class KioskHubView(APIView):
    permission_classes = [_HubPerm]

    def get(self, request: Request) -> Response:
        return Response({"widgets": get_hub_widgets(request.user, kiosk_mode=True)})


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
