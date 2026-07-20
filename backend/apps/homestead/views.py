"""homestead views — thin wrappers over selectors/services (Coding Standards §6)."""
from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.homestead import selectors, services
from apps.homestead.serializers import (
    ApplianceSerializer,
    ImprovementSerializer,
    MaintenanceTaskSerializer,
    PropertySerializer,
    ServiceProviderSerializer,
)
from apps.permissions.drf import HomeStackPermission

_Perm = HomeStackPermission.for_resource("homestead")


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class HomesteadSearchView(APIView):
    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        query = (request.query_params.get("q") or "").strip()
        if not query:
            return Response({"appliances": [], "maintenance": [], "providers": [], "improvements": []})
        r = selectors.search_homestead(request.user, query)
        return Response({
            "appliances": ApplianceSerializer(r["appliances"], many=True).data,
            "maintenance": MaintenanceTaskSerializer(r["maintenance"], many=True).data,
            "providers": ServiceProviderSerializer(r["providers"], many=True).data,
            "improvements": ImprovementSerializer(r["improvements"], many=True).data,
        })


# ---------------------------------------------------------------------------
# Property
# ---------------------------------------------------------------------------

class PropertyListView(APIView):
    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        return Response(PropertySerializer(selectors.list_properties(request.user), many=True).data)

    def post(self, request: Request) -> Response:
        serializer = PropertySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_property(request.user, **serializer.validated_data)
        return Response(PropertySerializer(obj).data, status=status.HTTP_201_CREATED)


class PropertyDetailView(APIView):
    permission_classes = [_Perm]

    def _get(self, pk: int):
        obj = selectors.get_property(pk)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, property_id: int) -> Response:
        obj = self._get(property_id)
        serializer = PropertySerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_property(request.user, obj, **serializer.validated_data)
        return Response(PropertySerializer(obj).data)

    def delete(self, request: Request, property_id: int) -> Response:
        services.delete_property(request.user, self._get(property_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Service providers
# ---------------------------------------------------------------------------

class ProviderListView(APIView):
    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        return Response(ServiceProviderSerializer(selectors.list_providers(request.user), many=True).data)

    def post(self, request: Request) -> Response:
        serializer = ServiceProviderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_provider(request.user, **serializer.validated_data)
        return Response(ServiceProviderSerializer(obj).data, status=status.HTTP_201_CREATED)


class ProviderDetailView(APIView):
    permission_classes = [_Perm]

    def _get(self, pk: int):
        obj = selectors.get_provider(pk)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, provider_id: int) -> Response:
        obj = self._get(provider_id)
        serializer = ServiceProviderSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_provider(request.user, obj, **serializer.validated_data)
        return Response(ServiceProviderSerializer(obj).data)

    def delete(self, request: Request, provider_id: int) -> Response:
        services.delete_provider(request.user, self._get(provider_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Appliances
# ---------------------------------------------------------------------------

class ApplianceListView(APIView):
    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        appliances = selectors.list_appliances(
            request.user, expiring_only=request.query_params.get("expiring") == "1"
        )
        return Response(ApplianceSerializer(appliances, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = ApplianceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_appliance(request.user, **serializer.validated_data)
        return Response(ApplianceSerializer(obj).data, status=status.HTTP_201_CREATED)


class ApplianceDetailView(APIView):
    permission_classes = [_Perm]

    def _get(self, pk: int):
        obj = selectors.get_appliance(pk)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, appliance_id: int) -> Response:
        obj = self._get(appliance_id)
        serializer = ApplianceSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_appliance(request.user, obj, **serializer.validated_data)
        return Response(ApplianceSerializer(obj).data)

    def delete(self, request: Request, appliance_id: int) -> Response:
        services.delete_appliance(request.user, self._get(appliance_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------

class MaintenanceListView(APIView):
    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        tasks = selectors.list_maintenance(
            request.user, due_only=request.query_params.get("due") == "1"
        )
        return Response(MaintenanceTaskSerializer(tasks, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = MaintenanceTaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_maintenance(request.user, **serializer.validated_data)
        return Response(MaintenanceTaskSerializer(obj).data, status=status.HTTP_201_CREATED)


class MaintenanceDetailView(APIView):
    permission_classes = [_Perm]

    def _get(self, pk: int):
        obj = selectors.get_maintenance(pk)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, task_id: int) -> Response:
        obj = self._get(task_id)
        serializer = MaintenanceTaskSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_maintenance(request.user, obj, **serializer.validated_data)
        return Response(MaintenanceTaskSerializer(obj).data)

    def delete(self, request: Request, task_id: int) -> Response:
        services.delete_maintenance(request.user, self._get(task_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class MaintenanceCompleteView(APIView):
    """Mark a task done — stamps last_done_at and advances next_due_at (RRULE)."""
    permission_classes = [_Perm]
    permission_action = "edit"

    def post(self, request: Request, task_id: int) -> Response:
        obj = selectors.get_maintenance(task_id)
        if obj is None:
            raise NotFound()
        obj = services.complete_maintenance(request.user, obj)
        return Response(MaintenanceTaskSerializer(obj).data)


# ---------------------------------------------------------------------------
# Improvements
# ---------------------------------------------------------------------------

class ImprovementListView(APIView):
    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        improvements = selectors.list_improvements(
            request.user, open_only=request.query_params.get("open") == "1"
        )
        return Response(ImprovementSerializer(improvements, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = ImprovementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_improvement(request.user, **serializer.validated_data)
        return Response(ImprovementSerializer(obj).data, status=status.HTTP_201_CREATED)


class ImprovementDetailView(APIView):
    permission_classes = [_Perm]

    def _get(self, pk: int):
        obj = selectors.get_improvement(pk)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, improvement_id: int) -> Response:
        obj = self._get(improvement_id)
        serializer = ImprovementSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_improvement(request.user, obj, **serializer.validated_data)
        return Response(ImprovementSerializer(obj).data)

    def delete(self, request: Request, improvement_id: int) -> Response:
        services.delete_improvement(request.user, self._get(improvement_id))
        return Response(status=status.HTTP_204_NO_CONTENT)
