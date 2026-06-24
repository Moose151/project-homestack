"""hub views — GET /hub/ and GET /kiosk/hub/."""
from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.hub.services import get_hub_widgets
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
