"""
core views — household endpoint.

GET   /api/v1/household/   — return the single household (household.view)
PATCH /api/v1/household/   — update name/timezone/locale (household.edit, admin only)
"""
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core import selectors, services
from apps.core.serializers import HouseholdSerializer, HouseholdWriteSerializer
from apps.permissions.drf import HomeStackPermission

_HouseholdPerm = HomeStackPermission.for_resource("household")


class HouseholdView(APIView):
    permission_classes = [_HouseholdPerm]
    # GET → "view", PATCH → "edit" — both handled by the same resolver mapping

    def get(self, request: Request) -> Response:
        household = selectors.get_household()
        return Response(HouseholdSerializer(household).data)

    def patch(self, request: Request) -> Response:
        household = selectors.get_household()
        serializer = HouseholdWriteSerializer(household, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = services.update_household(request.user, **serializer.validated_data)
        return Response(HouseholdSerializer(updated).data)
