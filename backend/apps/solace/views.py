"""solace views — thin API layer with finance re-auth/audit gate."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

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
    BillOccurrenceSerializer,
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


def _schedule_range(request: Request) -> tuple[date, date]:
    today = date.today()
    start_value = (request.query_params.get("start") or "").strip()
    end_value = (request.query_params.get("end") or "").strip()
    try:
        start = date.fromisoformat(start_value) if start_value else today.replace(day=1)
        if end_value:
            end = date.fromisoformat(end_value)
        else:
            next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
            end = next_month - timedelta(days=1)
    except ValueError as exc:
        raise ValidationError({"date": "Schedule dates must use YYYY-MM-DD."}) from exc
    if end < start:
        raise ValidationError({"end": "End date must be on or after start date."})
    if end - start > timedelta(days=370):
        raise ValidationError({"end": "Schedule windows cannot exceed 370 days."})
    return start, end


class SolaceScheduleView(SolaceAccessMixin, APIView):
    def get(self, request: Request) -> Response:
        from apps.solace.bill_schedule import ensure_bill_occurrences
        from apps.solace.budget_engine import payday_occurrences

        start, end = _schedule_range(request)
        for bill in selectors.list_bills(request.user, active_only=True):
            ensure_bill_occurrences(bill, start, end)
        occurrences = selectors.list_bill_occurrences(request.user, start=start, end=end)
        income_events = []
        for payday in selectors.list_paydays(request.user, active_only=True):
            for due_at in payday_occurrences(payday, start, end):
                income_events.append(
                    {
                        "payday_id": payday.id,
                        "title": payday.title,
                        "due_at": due_at,
                        "amount": f"{payday.expected_amount:.2f}",
                    }
                )
        income_events.sort(key=lambda row: (row["due_at"], row["title"].lower()))
        bills_total = sum((row.amount for row in occurrences), Decimal("0.00"))
        paid_total = sum(
            (row.amount for row in occurrences if row.status == row.Status.PAID),
            Decimal("0.00"),
        )
        skipped_total = sum(
            (row.amount for row in occurrences if row.status == row.Status.SKIPPED),
            Decimal("0.00"),
        )
        income_total = sum(
            (Decimal(row["amount"]) for row in income_events),
            Decimal("0.00"),
        )
        return Response(
            {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "occurrences": BillOccurrenceSerializer(occurrences, many=True).data,
                "income_events": income_events,
                "summary": {
                    "bills_total": f"{bills_total:.2f}",
                    "paid_total": f"{paid_total:.2f}",
                    "unpaid_total": f"{bills_total - paid_total - skipped_total:.2f}",
                    "skipped_total": f"{skipped_total:.2f}",
                    "income_total": f"{income_total:.2f}",
                },
            }
        )


class BillOccurrenceActionView(SolaceAccessMixin, APIView):
    permission_action = "edit"

    def post(self, request: Request, occurrence_id: int, action: str) -> Response:
        occurrence = selectors.get_bill_occurrence(request.user, occurrence_id)
        if occurrence is None:
            raise NotFound()
        actions = {
            "paid": services.mark_occurrence_paid,
            "unpaid": services.mark_occurrence_unpaid,
            "skip": services.skip_occurrence,
        }
        handler = actions.get(action)
        if handler is None:
            raise NotFound()
        return Response(BillOccurrenceSerializer(handler(request.user, occurrence)).data)


class BillListView(SolaceAccessMixin, APIView):
    def get(self, request: Request) -> Response:
        bills = selectors.list_bills(
            request.user,
            upcoming_only=request.query_params.get("upcoming") == "1",
            unpaid_only=request.query_params.get("unpaid") == "1",
        )
        from apps.solace.bill_schedule import ensure_bill_occurrences

        today = date.today()
        for bill in bills:
            ensure_bill_occurrences(
                bill,
                today - timedelta(days=365),
                today + timedelta(days=550),
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
