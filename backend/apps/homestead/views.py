"""homestead views — thin wrappers over selectors/services (Coding Standards §6)."""
from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.homestead import selectors, services
from apps.homestead.serializers import (
    ApplianceSerializer,
    HouseholdCostSerializer,
    ImprovementSerializer,
    InsurancePolicySerializer,
    MaintenanceCostRequestSerializer,
    MaintenanceTaskSerializer,
    PoolReadingAssessmentSerializer,
    PoolSerializer,
    PoolTargetSerializer,
    PropertySerializer,
    RoomAreaSerializer,
    RoomPlanItemSerializer,
    RoomPlanProductSerializer,
    ServiceProviderSerializer,
    UtilityBillSerializer,
    UtilitySeriesSerializer,
    WaterTestSerializer,
)
from apps.nodes.access import sensitive_node_access
from apps.permissions.drf import HomeStackPermission

_Perm = HomeStackPermission.for_resource("homestead")
_SolacePerm = HomeStackPermission.for_resource("solace")


class HomesteadFinanceAccessMixin(
    sensitive_node_access("homestead", surface="costs_cover")
):
    """Home costs and cover need Money permission as well as the shared sensitive gate.

    Before this used the shared gate it always demanded a password, ignoring the household
    setting that Solace honoured — so turning the prompt off left one finance surface still
    asking for it.
    """

    permission_classes = [_Perm, _SolacePerm]


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class HomesteadSearchView(APIView):
    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        query = (request.query_params.get("q") or "").strip()
        if not query:
            return Response({
                "appliances": [], "maintenance": [], "providers": [], "improvements": [],
                "rooms": [], "room_items": [],
            })
        r = selectors.search_homestead(request.user, query)
        return Response({
            "appliances": ApplianceSerializer(r["appliances"], many=True).data,
            "maintenance": MaintenanceTaskSerializer(r["maintenance"], many=True).data,
            "providers": ServiceProviderSerializer(r["providers"], many=True).data,
            "improvements": ImprovementSerializer(r["improvements"], many=True).data,
            "rooms": RoomAreaSerializer(r["rooms"], many=True).data,
            "room_items": RoomPlanItemSerializer(r["room_items"], many=True).data,
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


class MaintenanceCostView(HomesteadFinanceAccessMixin, APIView):
    """Create/update this task's one Solace cost without duplicating maintenance data."""

    finance_surface = "maintenance_cost"

    def post(self, request: Request, task_id: int) -> Response:
        obj = selectors.get_maintenance(task_id, request.user)
        if obj is None:
            raise NotFound()
        serializer = MaintenanceCostRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.request_maintenance_cost(
            request.user,
            obj,
            **serializer.validated_data,
        )
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
# Rooms / areas and unified plan items
# ---------------------------------------------------------------------------

def _room_serializer_context(user, rooms) -> tuple[dict, dict]:
    summaries, household = selectors.room_summaries(user, rooms)
    return {
        "summaries": summaries,
        "empty_summary": selectors.empty_room_summary(),
    }, household


class RoomListView(APIView):
    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        rooms = selectors.list_rooms(request.user)
        context, household = _room_serializer_context(request.user, rooms)
        return Response({
            "rooms": RoomAreaSerializer(rooms, many=True, context=context).data,
            "household_summary": household,
        })

    def post(self, request: Request) -> Response:
        serializer = RoomAreaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        room = services.create_room(request.user, **serializer.validated_data)
        context, _household = _room_serializer_context(request.user, [room])
        return Response(
            RoomAreaSerializer(room, context=context).data,
            status=status.HTTP_201_CREATED,
        )


class RoomDetailView(APIView):
    permission_classes = [_Perm]

    def _get(self, room_id: int, user):
        room = selectors.get_room(room_id, user)
        if room is None:
            raise NotFound()
        return room

    def get(self, request: Request, room_id: int) -> Response:
        room = self._get(room_id, request.user)
        items = selectors.list_room_items(request.user, room)
        summary = selectors.summarize_room_items(items)
        return Response({
            "room": RoomAreaSerializer(
                room,
                context={"summaries": {room.id: summary}, "empty_summary": summary},
            ).data,
            "items": RoomPlanItemSerializer(items, many=True).data,
            "summary": summary,
        })

    def patch(self, request: Request, room_id: int) -> Response:
        room = self._get(room_id, request.user)
        serializer = RoomAreaSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        room = services.update_room(request.user, room, **serializer.validated_data)
        context, _household = _room_serializer_context(request.user, [room])
        return Response(RoomAreaSerializer(room, context=context).data)

    def delete(self, request: Request, room_id: int) -> Response:
        services.delete_room(request.user, self._get(room_id, request.user))
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoomItemListView(APIView):
    permission_classes = [_Perm]

    def _room(self, room_id: int, user):
        room = selectors.get_room(room_id, user)
        if room is None:
            raise NotFound()
        return room

    def get(self, request: Request, room_id: int) -> Response:
        return Response(RoomPlanItemSerializer(
            selectors.list_room_items(request.user, self._room(room_id, request.user)),
            many=True,
        ).data)

    def post(self, request: Request, room_id: int) -> Response:
        room = self._room(room_id, request.user)
        serializer = RoomPlanItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = services.create_room_item(
            request.user, room, **serializer.validated_data
        )
        return Response(
            RoomPlanItemSerializer(item).data,
            status=status.HTTP_201_CREATED,
        )


class RoomItemDetailView(APIView):
    permission_classes = [_Perm]

    def _get(self, room_id: int, item_id: int, user):
        room = selectors.get_room(room_id, user)
        if room is None:
            raise NotFound()
        item = selectors.get_room_item(item_id, room, user)
        if item is None:
            raise NotFound()
        return item

    def patch(self, request: Request, room_id: int, item_id: int) -> Response:
        item = self._get(room_id, item_id, request.user)
        serializer = RoomPlanItemSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        item = services.update_room_item(
            request.user, item, **serializer.validated_data
        )
        return Response(RoomPlanItemSerializer(item).data)

    def delete(self, request: Request, room_id: int, item_id: int) -> Response:
        services.delete_room_item(
            request.user, self._get(room_id, item_id, request.user)
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class _RoomProductBase(APIView):
    """Shared lookup: a product is only reachable through a room + item the user may see."""

    permission_classes = [_Perm]

    def _item(self, room_id: int, item_id: int, user):
        room = selectors.get_room(room_id, user)
        if room is None:
            raise NotFound()
        item = selectors.get_room_item(item_id, room, user)
        if item is None:
            raise NotFound()
        return item


class RoomProductListView(_RoomProductBase):
    def get(self, request: Request, room_id: int, item_id: int) -> Response:
        item = self._item(room_id, item_id, request.user)
        return Response(RoomPlanProductSerializer(
            selectors.list_room_products(item), many=True
        ).data)

    def post(self, request: Request, room_id: int, item_id: int) -> Response:
        item = self._item(room_id, item_id, request.user)
        serializer = RoomPlanProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = services.create_room_product(
            request.user, item, **serializer.validated_data
        )
        return Response(
            RoomPlanProductSerializer(product).data,
            status=status.HTTP_201_CREATED,
        )


class RoomProductDetailView(_RoomProductBase):
    def _get(self, room_id: int, item_id: int, product_id: int, user):
        product = selectors.get_room_product(
            product_id, self._item(room_id, item_id, user)
        )
        if product is None:
            raise NotFound()
        return product

    def patch(self, request: Request, room_id: int, item_id: int, product_id: int) -> Response:
        product = self._get(room_id, item_id, product_id, request.user)
        serializer = RoomPlanProductSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        product = services.update_room_product(
            request.user, product, **serializer.validated_data
        )
        return Response(RoomPlanProductSerializer(product).data)

    def delete(self, request: Request, room_id: int, item_id: int, product_id: int) -> Response:
        services.delete_room_product(
            request.user, self._get(room_id, item_id, product_id, request.user)
        )
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


# ---------------------------------------------------------------------------
# Utility usage
# ---------------------------------------------------------------------------

class UtilityBillListView(APIView):
    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        bills = selectors.list_utility_bills(
            request.user, utility_type=request.query_params.get("type") or None
        )
        return Response(UtilityBillSerializer(bills, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = UtilityBillSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.log_utility_bill(request.user, **serializer.validated_data)
        return Response(UtilityBillSerializer(obj).data, status=status.HTTP_201_CREATED)


class UtilityBillDetailView(APIView):
    permission_classes = [_Perm]

    def _get(self, pk: int, user):
        obj = selectors.get_utility_bill(pk, user)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, bill_id: int) -> Response:
        obj = self._get(bill_id, request.user)
        serializer = UtilityBillSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_utility_bill(request.user, obj, **serializer.validated_data)
        return Response(UtilityBillSerializer(obj).data)

    def delete(self, request: Request, bill_id: int) -> Response:
        services.delete_utility_bill(request.user, self._get(bill_id, request.user))
        return Response(status=status.HTTP_204_NO_CONTENT)


class UtilityUsageView(APIView):
    """The charts: one series per utility, with per-day figures and comparisons."""

    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        series = selectors.utility_usage(
            request.user, utility_type=request.query_params.get("type") or None
        )
        return Response({"series": UtilitySeriesSerializer(series, many=True).data})


# ---------------------------------------------------------------------------
# Pools
# ---------------------------------------------------------------------------

class PoolListView(APIView):
    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        rows = selectors.list_pools(request.user, active_only=request.query_params.get("active") == "1")
        return Response(PoolSerializer(rows, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = PoolSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # A new pool arrives with its starter jobs unless the household opts out.
        with_schedule = request.data.get("with_care_schedule", True) is not False
        obj = services.create_pool(
            request.user, with_care_schedule=with_schedule, **serializer.validated_data
        )
        return Response(PoolSerializer(obj).data, status=status.HTTP_201_CREATED)


class PoolDetailView(APIView):
    permission_classes = [_Perm]

    def _get(self, request: Request, pool_id: int):
        obj = selectors.get_pool(pool_id, request.user)
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request: Request, pool_id: int) -> Response:
        return Response(PoolSerializer(self._get(request, pool_id)).data)

    def patch(self, request: Request, pool_id: int) -> Response:
        serializer = PoolSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_pool(request.user, self._get(request, pool_id), **serializer.validated_data)
        return Response(PoolSerializer(obj).data)

    def delete(self, request: Request, pool_id: int) -> Response:
        services.delete_pool(request.user, self._get(request, pool_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class PoolStatusView(APIView):
    """Is the water balanced, what does each reading mean, and what care is due."""

    permission_classes = [_Perm]

    def get(self, request: Request, pool_id: int) -> Response:
        pool = selectors.get_pool(pool_id, request.user)
        if pool is None:
            raise NotFound()
        status_data = selectors.pool_status(request.user, pool)
        return Response({
            **status_data,
            "readings": {
                key: PoolReadingAssessmentSerializer(row).data
                for key, row in status_data["readings"].items()
            },
            "targets": {
                key: PoolTargetSerializer(row).data
                for key, row in selectors.pool_targets(pool).items()
            },
            "care_tasks": MaintenanceTaskSerializer(
                selectors.list_pool_care(request.user, pool), many=True
            ).data,
        })


class PoolCareScheduleView(APIView):
    """Add the starter care jobs this pool is missing. Safe to call more than once."""

    permission_classes = [_Perm]
    permission_action = "edit"

    def post(self, request: Request, pool_id: int) -> Response:
        pool = selectors.get_pool(pool_id, request.user)
        if pool is None:
            raise NotFound()
        created = services.apply_care_schedule(request.user, pool)
        return Response(
            {"created": MaintenanceTaskSerializer(created, many=True).data},
            status=status.HTTP_201_CREATED,
        )


class WaterTestListView(APIView):
    permission_classes = [_Perm]

    def _pool(self, request: Request, pool_id: int):
        pool = selectors.get_pool(pool_id, request.user)
        if pool is None:
            raise NotFound()
        return pool

    def get(self, request: Request, pool_id: int) -> Response:
        rows = selectors.list_water_tests(self._pool(request, pool_id))
        return Response(WaterTestSerializer(rows, many=True).data)

    def post(self, request: Request, pool_id: int) -> Response:
        pool = self._pool(request, pool_id)
        serializer = WaterTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.log_water_test(request.user, pool, **serializer.validated_data)
        return Response(WaterTestSerializer(obj).data, status=status.HTTP_201_CREATED)


class WaterTestDetailView(APIView):
    permission_classes = [_Perm]

    def _get(self, request: Request, pool_id: int, test_id: int):
        pool = selectors.get_pool(pool_id, request.user)
        if pool is None:
            raise NotFound()
        obj = selectors.get_water_test(test_id, pool)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, pool_id: int, test_id: int) -> Response:
        serializer = WaterTestSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_water_test(
            request.user, self._get(request, pool_id, test_id), **serializer.validated_data
        )
        return Response(WaterTestSerializer(obj).data)

    def delete(self, request: Request, pool_id: int, test_id: int) -> Response:
        services.delete_water_test(request.user, self._get(request, pool_id, test_id))
        return Response(status=status.HTTP_204_NO_CONTENT)
