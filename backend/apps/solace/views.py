"""solace views — thin API layer with finance re-auth/audit gate."""
from __future__ import annotations

from datetime import date

from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.services import is_reauthed
from apps.audit.helpers import log_audit
from apps.nodes.models import Node
from apps.permissions.drf import HomeStackPermission
from apps.solace import selectors, services
from apps.solace.serializers import (
    BillSerializer,
    BudgetBucketSerializer,
    PaydayChecklistItemSerializer,
    PaydaySerializer,
    PlannedPurchaseSerializer,
    SubscriptionSerializer,
)

_Perm = HomeStackPermission.for_resource("solace")


class SolaceAccessMixin:
    permission_classes = [_Perm]

    def initial(self, request: Request, *args, **kwargs) -> None:
        super().initial(request, *args, **kwargs)
        if not is_reauthed(request._request):
            raise PermissionDenied("Password re-authentication required for Solace.")
        node = Node.objects.filter(key="solace").first()
        log_audit(
            "sensitive_node_accessed",
            user=request.user,
            target_node=node,
            request=request._request,
            metadata={"node": "solace", "path": request.path, "method": request.method},
        )


class SolaceSearchView(SolaceAccessMixin, APIView):
    def get(self, request: Request) -> Response:
        query = (request.query_params.get("q") or "").strip()
        empty = {"bills": [], "paydays": [], "purchases": [], "buckets": [], "subscriptions": [], "checklist": []}
        if not query:
            return Response(empty)
        r = selectors.search_solace(request.user, query)
        return Response({
            "bills": BillSerializer(r["bills"], many=True).data,
            "paydays": PaydaySerializer(r["paydays"], many=True).data,
            "purchases": PlannedPurchaseSerializer(r["purchases"], many=True).data,
            "buckets": BudgetBucketSerializer(r["buckets"], many=True).data,
            "subscriptions": SubscriptionSerializer(r["subscriptions"], many=True).data,
            "checklist": PaydayChecklistItemSerializer(r["checklist"], many=True).data,
        })


def _plan_date(request: Request):
    value = (request.query_params.get("date") or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError({"date": "Use YYYY-MM-DD."}) from exc


class PayCyclePlanView(SolaceAccessMixin, APIView):
    def get(self, request: Request) -> Response:
        return Response(selectors.get_pay_cycle_plan(request.user, as_of=_plan_date(request)))


class PayCycleChecklistView(SolaceAccessMixin, APIView):
    permission_action = "edit"

    def post(self, request: Request) -> Response:
        plan = selectors.get_pay_cycle_plan(request.user, as_of=_plan_date(request))
        items = services.generate_plan_checklist(request.user, plan)
        return Response(PaydayChecklistItemSerializer(items, many=True).data)


class BillListView(SolaceAccessMixin, APIView):
    def get(self, request: Request) -> Response:
        bills = selectors.list_bills(
            request.user,
            upcoming_only=request.query_params.get("upcoming") == "1",
            unpaid_only=request.query_params.get("unpaid") == "1",
        )
        return Response(BillSerializer(bills, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = BillSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_bill(request.user, **serializer.validated_data)
        return Response(BillSerializer(obj).data, status=status.HTTP_201_CREATED)


class BillDetailView(SolaceAccessMixin, APIView):
    def _get(self, pk: int):
        obj = selectors.get_bill(pk)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, bill_id: int) -> Response:
        serializer = BillSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_bill(request.user, self._get(bill_id), **serializer.validated_data)
        return Response(BillSerializer(obj).data)

    def delete(self, request: Request, bill_id: int) -> Response:
        services.delete_bill(request.user, self._get(bill_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class BillPaidView(SolaceAccessMixin, APIView):
    permission_action = "edit"

    def post(self, request: Request, bill_id: int) -> Response:
        obj = selectors.get_bill(bill_id)
        if obj is None:
            raise NotFound()
        return Response(BillSerializer(services.mark_bill_paid(request.user, obj)).data)


class PaydayListView(SolaceAccessMixin, APIView):
    def get(self, request: Request) -> Response:
        paydays = selectors.list_paydays(request.user, upcoming_only=request.query_params.get("upcoming") == "1")
        return Response(PaydaySerializer(paydays, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = PaydaySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(PaydaySerializer(services.create_payday(request.user, **serializer.validated_data)).data, status=201)


class PaydayDetailView(SolaceAccessMixin, APIView):
    def _get(self, pk: int):
        obj = selectors.get_payday(pk)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, payday_id: int) -> Response:
        serializer = PaydaySerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(PaydaySerializer(services.update_payday(request.user, self._get(payday_id), **serializer.validated_data)).data)

    def delete(self, request: Request, payday_id: int) -> Response:
        services.delete_payday(request.user, self._get(payday_id))
        return Response(status=204)


class PurchaseListView(SolaceAccessMixin, APIView):
    def get(self, request: Request) -> Response:
        purchases = selectors.list_purchases(request.user, open_only=request.query_params.get("open") == "1")
        return Response(PlannedPurchaseSerializer(purchases, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = PlannedPurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(PlannedPurchaseSerializer(services.create_purchase(request.user, **serializer.validated_data)).data, status=201)


class PurchaseDetailView(SolaceAccessMixin, APIView):
    def _get(self, pk: int):
        obj = selectors.get_purchase(pk)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, purchase_id: int) -> Response:
        serializer = PlannedPurchaseSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(PlannedPurchaseSerializer(services.update_purchase(request.user, self._get(purchase_id), **serializer.validated_data)).data)

    def delete(self, request: Request, purchase_id: int) -> Response:
        services.delete_purchase(request.user, self._get(purchase_id))
        return Response(status=204)


class BucketListView(SolaceAccessMixin, APIView):
    def get(self, request: Request) -> Response:
        return Response(BudgetBucketSerializer(selectors.list_buckets(request.user), many=True).data)

    def post(self, request: Request) -> Response:
        serializer = BudgetBucketSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(BudgetBucketSerializer(services.create_bucket(request.user, **serializer.validated_data)).data, status=201)


class BucketDetailView(SolaceAccessMixin, APIView):
    def _get(self, pk: int):
        obj = selectors.get_bucket(pk)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, bucket_id: int) -> Response:
        serializer = BudgetBucketSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(BudgetBucketSerializer(services.update_bucket(request.user, self._get(bucket_id), **serializer.validated_data)).data)

    def delete(self, request: Request, bucket_id: int) -> Response:
        services.delete_bucket(request.user, self._get(bucket_id))
        return Response(status=204)


class SubscriptionListView(SolaceAccessMixin, APIView):
    def get(self, request: Request) -> Response:
        subscriptions = selectors.list_subscriptions(request.user, active_only=request.query_params.get("active") == "1")
        return Response(SubscriptionSerializer(subscriptions, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = SubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(SubscriptionSerializer(services.create_subscription(request.user, **serializer.validated_data)).data, status=201)


class SubscriptionDetailView(SolaceAccessMixin, APIView):
    def _get(self, pk: int):
        obj = selectors.get_subscription(pk)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, subscription_id: int) -> Response:
        serializer = SubscriptionSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(SubscriptionSerializer(services.update_subscription(request.user, self._get(subscription_id), **serializer.validated_data)).data)

    def delete(self, request: Request, subscription_id: int) -> Response:
        services.delete_subscription(request.user, self._get(subscription_id))
        return Response(status=204)


class ChecklistListView(SolaceAccessMixin, APIView):
    def get(self, request: Request) -> Response:
        items = selectors.list_checklist_items(
            request.user,
            incomplete_only=request.query_params.get("incomplete") == "1",
            latest_cycle_only=request.query_params.get("latest") == "1",
        )
        return Response(PaydayChecklistItemSerializer(items, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = PaydayChecklistItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(PaydayChecklistItemSerializer(services.create_checklist_item(request.user, **serializer.validated_data)).data, status=201)


class ChecklistDetailView(SolaceAccessMixin, APIView):
    def _get(self, pk: int):
        obj = selectors.get_checklist_item(pk)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, item_id: int) -> Response:
        serializer = PaydayChecklistItemSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(PaydayChecklistItemSerializer(services.update_checklist_item(request.user, self._get(item_id), **serializer.validated_data)).data)

    def delete(self, request: Request, item_id: int) -> Response:
        services.delete_checklist_item(request.user, self._get(item_id))
        return Response(status=204)
