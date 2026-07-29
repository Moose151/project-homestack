"""homestead views — thin wrappers over selectors/services (Coding Standards §6)."""
from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.services import is_reauthed
from apps.audit.helpers import log_audit
from apps.homestead import selectors, services
from apps.homestead.serializers import (
    ApplianceSerializer,
    HouseholdCostSerializer,
    ImprovementSerializer,
    InsurancePolicySerializer,
    MaintenanceTaskSerializer,
    PropertySerializer,
    ServiceProviderSerializer,
)
from apps.nodes.models import Node
from apps.permissions.drf import HomeStackPermission

_Perm = HomeStackPermission.for_resource("homestead")
_SolacePerm = HomeStackPermission.for_resource("solace")


class HomesteadFinanceAccessMixin:
    """Require both node permissions, password re-auth and an audit trail."""

    permission_classes = [_Perm, _SolacePerm]

    def initial(self, request: Request, *args, **kwargs) -> None:
        super().initial(request, *args, **kwargs)
        if not is_reauthed(request._request):
            raise PermissionDenied("Password re-authentication required for home costs.")
        node = Node.objects.filter(key="homestead").first()
        log_audit(
            "sensitive_node_accessed",
            user=request.user,
            target_node=node,
            request=request._request,
            metadata={
                "node": "homestead",
                "surface": "costs_cover",
                "path": request.path,
                "method": request.method,
            },
        )


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

    def _get(self, pk: int, user):
        obj = selectors.get_property(pk, user)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, property_id: int) -> Response:
        obj = self._get(property_id, request.user)
        serializer = PropertySerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_property(request.user, obj, **serializer.validated_data)
        return Response(PropertySerializer(obj).data)

    def delete(self, request: Request, property_id: int) -> Response:
        services.delete_property(request.user, self._get(property_id, request.user))
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

    def _get(self, pk: int, user):
        obj = selectors.get_provider(pk, user)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, provider_id: int) -> Response:
        obj = self._get(provider_id, request.user)
        serializer = ServiceProviderSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_provider(request.user, obj, **serializer.validated_data)
        return Response(ServiceProviderSerializer(obj).data)

    def delete(self, request: Request, provider_id: int) -> Response:
        services.delete_provider(request.user, self._get(provider_id, request.user))
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

    def _get(self, pk: int, user):
        obj = selectors.get_appliance(pk, user)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, appliance_id: int) -> Response:
        obj = self._get(appliance_id, request.user)
        serializer = ApplianceSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_appliance(request.user, obj, **serializer.validated_data)
        return Response(ApplianceSerializer(obj).data)

    def delete(self, request: Request, appliance_id: int) -> Response:
        services.delete_appliance(request.user, self._get(appliance_id, request.user))
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

    def _get(self, pk: int, user):
        obj = selectors.get_maintenance(pk, user)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, task_id: int) -> Response:
        obj = self._get(task_id, request.user)
        serializer = MaintenanceTaskSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_maintenance(request.user, obj, **serializer.validated_data)
        return Response(MaintenanceTaskSerializer(obj).data)

    def delete(self, request: Request, task_id: int) -> Response:
        services.delete_maintenance(request.user, self._get(task_id, request.user))
        return Response(status=status.HTTP_204_NO_CONTENT)


class MaintenanceCompleteView(APIView):
    """Mark a task done — stamps last_done_at and advances next_due_at (RRULE)."""
    permission_classes = [_Perm]
    permission_action = "edit"

    def post(self, request: Request, task_id: int) -> Response:
        obj = selectors.get_maintenance(task_id, request.user)
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

    def _get(self, pk: int, user):
        obj = selectors.get_improvement(pk, user)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, improvement_id: int) -> Response:
        obj = self._get(improvement_id, request.user)
        serializer = ImprovementSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_improvement(request.user, obj, **serializer.validated_data)
        return Response(ImprovementSerializer(obj).data)

    def delete(self, request: Request, improvement_id: int) -> Response:
        services.delete_improvement(request.user, self._get(improvement_id, request.user))
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Protected costs & cover
# ---------------------------------------------------------------------------

class InsurancePolicyListView(HomesteadFinanceAccessMixin, APIView):
    def get(self, request: Request) -> Response:
        rows = selectors.list_insurance_policies(
            request.user, active_only=request.query_params.get("active") == "1"
        )
        return Response(InsurancePolicySerializer(rows, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = InsurancePolicySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_insurance_policy(request.user, **serializer.validated_data)
        return Response(InsurancePolicySerializer(obj).data, status=status.HTTP_201_CREATED)


class InsurancePolicyDetailView(HomesteadFinanceAccessMixin, APIView):
    def _get(self, pk: int, user):
        obj = selectors.get_insurance_policy(pk, user)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, policy_id: int) -> Response:
        serializer = InsurancePolicySerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_insurance_policy(
            request.user, self._get(policy_id, request.user), **serializer.validated_data
        )
        return Response(InsurancePolicySerializer(obj).data)

    def delete(self, request: Request, policy_id: int) -> Response:
        services.delete_insurance_policy(
            request.user, self._get(policy_id, request.user)
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class HouseholdCostListView(HomesteadFinanceAccessMixin, APIView):
    def get(self, request: Request) -> Response:
        rows = selectors.list_household_costs(
            request.user, active_only=request.query_params.get("active") == "1"
        )
        return Response(HouseholdCostSerializer(rows, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = HouseholdCostSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_household_cost(request.user, **serializer.validated_data)
        return Response(HouseholdCostSerializer(obj).data, status=status.HTTP_201_CREATED)


class HouseholdCostDetailView(HomesteadFinanceAccessMixin, APIView):
    def _get(self, pk: int, user):
        obj = selectors.get_household_cost(pk, user)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, cost_id: int) -> Response:
        serializer = HouseholdCostSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_household_cost(
            request.user, self._get(cost_id, request.user), **serializer.validated_data
        )
        return Response(HouseholdCostSerializer(obj).data)

    def delete(self, request: Request, cost_id: int) -> Response:
        services.delete_household_cost(request.user, self._get(cost_id, request.user))
        return Response(status=status.HTTP_204_NO_CONTENT)
