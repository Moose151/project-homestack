"""solace views — thin API layer with finance re-auth/audit gate."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.services import is_reauthed
from apps.audit.helpers import log_audit
from apps.nodes.models import Node
from apps.permissions.drf import HomeStackPermission
from apps.solace import selectors, services
from apps.solace.serializers import (
    AccountBalanceSnapshotSerializer,
    BillOccurrenceSerializer,
    BillSerializer,
    BudgetBucketSerializer,
    CycleCloseoutSerializer,
    FinanceCategorySerializer,
    PaydayChecklistItemSerializer,
    PaydayChecklistPreferenceSerializer,
    PaydaySerializer,
    PlannedPurchaseSerializer,
    SolaceSettingsSerializer,
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


class SolaceSettingsView(SolaceAccessMixin, APIView):
    def _get(self, request: Request):
        return selectors.get_settings() or services.get_or_create_settings(request.user)

    def get(self, request: Request) -> Response:
        return Response(SolaceSettingsSerializer(self._get(request)).data)

    def patch(self, request: Request) -> Response:
        serializer = SolaceSettingsSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_settings(
            request.user,
            self._get(request),
            **serializer.validated_data,
        )
        return Response(SolaceSettingsSerializer(obj).data)


class FinanceCategoryListView(SolaceAccessMixin, APIView):
    def get(self, request: Request) -> Response:
        rows = selectors.list_categories(
            request.user,
            active_only=request.query_params.get("active") == "1",
            category_type=(request.query_params.get("type") or "").strip(),
        )
        return Response(FinanceCategorySerializer(rows, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = FinanceCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_category(request.user, **serializer.validated_data)
        return Response(FinanceCategorySerializer(obj).data, status=status.HTTP_201_CREATED)


class FinanceCategoryDetailView(SolaceAccessMixin, APIView):
    def _get(self, category_id: int):
        obj = selectors.get_category(category_id)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, category_id: int) -> Response:
        existing = self._get(category_id)
        serializer = FinanceCategorySerializer(existing, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_category(
            request.user,
            existing,
            **serializer.validated_data,
        )
        return Response(FinanceCategorySerializer(obj).data)

    def delete(self, request: Request, category_id: int) -> Response:
        existing = self._get(category_id)
        if existing.name.casefold() == "other":
            raise ValidationError({"detail": "The Other fallback category cannot be deleted."})
        services.delete_category(request.user, existing)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountBalanceListView(SolaceAccessMixin, APIView):
    def get(self, request: Request) -> Response:
        try:
            limit = min(100, max(1, int(request.query_params.get("limit", "25"))))
        except ValueError as exc:
            raise ValidationError({"limit": "Use a whole number."}) from exc
        rows = selectors.list_balance_snapshots(request.user, limit=limit)
        return Response(AccountBalanceSnapshotSerializer(rows, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = AccountBalanceSnapshotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_balance_snapshot(request.user, **serializer.validated_data)
        return Response(
            AccountBalanceSnapshotSerializer(obj).data,
            status=status.HTTP_201_CREATED,
        )


class AccountBalanceDetailView(SolaceAccessMixin, APIView):
    def _get(self, balance_id: int):
        obj = selectors.get_balance_snapshot(balance_id)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, balance_id: int) -> Response:
        serializer = AccountBalanceSnapshotSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_balance_snapshot(
            request.user,
            self._get(balance_id),
            **serializer.validated_data,
        )
        return Response(AccountBalanceSnapshotSerializer(obj).data)

    def delete(self, request: Request, balance_id: int) -> Response:
        services.delete_balance_snapshot(request.user, self._get(balance_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChecklistPreferenceView(SolaceAccessMixin, APIView):
    def get(self, request: Request) -> Response:
        rows = selectors.list_checklist_preferences(
            request.user,
            hidden_only=request.query_params.get("hidden") == "1",
        )
        return Response(PaydayChecklistPreferenceSerializer(rows, many=True).data)

    def post(self, request: Request) -> Response:
        source_key = str(request.data.get("source_key") or "").strip()
        label = str(request.data.get("label") or "").strip()
        if not source_key or not label:
            raise ValidationError({"source_key": "Source key and label are required."})
        obj = services.set_checklist_preference(
            request.user,
            source_key=source_key,
            label=label,
            is_hidden=bool(request.data.get("is_hidden", True)),
            reason=str(request.data.get("reason") or "").strip(),
        )
        return Response(PaydayChecklistPreferenceSerializer(obj).data)


def _cycle_context(request: Request) -> dict:
    from apps.solace.bill_schedule import ensure_bill_occurrences
    from apps.solace.models import BillOccurrence, SolaceSettings

    plan = selectors.get_pay_cycle_plan(request.user, as_of=_plan_date(request))
    cycle_start = date.fromisoformat(plan["cycle_start"])
    cycle_end = date.fromisoformat(plan["cycle_end"])
    settings_obj = selectors.get_settings() or services.get_or_create_settings(request.user)
    previous_cycle = (
        settings_obj.payday_bill_handling == SolaceSettings.PaydayBillHandling.PREVIOUS_CYCLE
    )
    bill_start = cycle_start + timedelta(days=1) if previous_cycle else cycle_start
    bill_end = cycle_end + timedelta(days=1) if previous_cycle else cycle_end
    for bill in selectors.list_bills(request.user, active_only=True):
        ensure_bill_occurrences(bill, bill_start, bill_end)
    occurrences = selectors.list_bill_occurrences(
        request.user,
        start=bill_start,
        end=bill_end,
    )
    unpaid = [
        row for row in occurrences
        if row.status == BillOccurrence.Status.UPCOMING
    ]
    latest_balance = selectors.get_latest_balance(request.user)
    unpaid_total = sum((row.amount for row in unpaid), Decimal("0.00"))
    projected = Decimal(latest_balance.balance) - unpaid_total if latest_balance else None
    closeout = selectors.get_cycle_closeout(cycle_start)
    checklist = selectors.list_checklist_items(request.user, cycle_start=cycle_start)
    return {
        "plan": plan,
        "cycle_start": cycle_start,
        "cycle_end": cycle_end,
        "bill_start": bill_start,
        "bill_end": bill_end,
        "occurrences": occurrences,
        "latest_balance": latest_balance,
        "projected_balance": projected,
        "closeout": closeout,
        "checklist": checklist,
        "settings": settings_obj,
        "unpaid_total": unpaid_total,
    }


class CycleCloseoutView(SolaceAccessMixin, APIView):
    def get(self, request: Request) -> Response:
        context = _cycle_context(request)
        occurrences = context["occurrences"]
        paid_total = sum(
            (row.amount for row in occurrences if row.status == row.Status.PAID),
            Decimal("0.00"),
        )
        skipped_total = sum(
            (row.amount for row in occurrences if row.status == row.Status.SKIPPED),
            Decimal("0.00"),
        )
        return Response(
            {
                "plan": context["plan"],
                "bill_window": {
                    "start": context["bill_start"].isoformat(),
                    "end": context["bill_end"].isoformat(),
                },
                "occurrences": BillOccurrenceSerializer(occurrences, many=True).data,
                "checklist": PaydayChecklistItemSerializer(
                    context["checklist"],
                    many=True,
                ).data,
                "latest_balance": (
                    AccountBalanceSnapshotSerializer(context["latest_balance"]).data
                    if context["latest_balance"] else None
                ),
                "projected_balance": (
                    f"{context['projected_balance']:.2f}"
                    if context["projected_balance"] is not None else None
                ),
                "closeout": (
                    CycleCloseoutSerializer(context["closeout"]).data
                    if context["closeout"] else None
                ),
                "summary": {
                    "bills_total": f"{sum((row.amount for row in occurrences), Decimal('0.00')):.2f}",
                    "paid_total": f"{paid_total:.2f}",
                    "unpaid_total": f"{context['unpaid_total']:.2f}",
                    "skipped_total": f"{skipped_total:.2f}",
                    "unpaid_count": sum(1 for row in occurrences if row.status == row.Status.UPCOMING),
                    "checklist_count": len(context["checklist"]),
                    "checklist_complete_count": sum(
                        1 for row in context["checklist"] if row.is_complete
                    ),
                },
            }
        )

    def post(self, request: Request) -> Response:
        context = _cycle_context(request)
        action = str(request.data.get("action") or "close").strip()
        if action not in {"close", "reopen"}:
            raise ValidationError({"action": "Use close or reopen."})
        obj = services.set_cycle_closeout(
            request.user,
            cycle_start=context["cycle_start"],
            cycle_end=context["cycle_end"],
            closed=action == "close",
            notes=str(request.data.get("notes") or "").strip(),
        )
        return Response(CycleCloseoutSerializer(obj).data)


class SolaceHealthView(SolaceAccessMixin, APIView):
    def get(self, request: Request) -> Response:
        from apps.solace.bill_schedule import ensure_bill_occurrences
        from apps.solace.models import BudgetBucket

        today = _plan_date(request) or timezone.localdate()
        paydays = selectors.list_paydays(request.user, active_only=True)
        bills = selectors.list_bills(request.user, active_only=True)
        buckets = selectors.list_buckets(request.user, active_only=True)
        issues = []
        if not paydays:
            issues.append({"level": "error", "code": "no_income", "message": "Add an active income source to calculate pay cycles."})
        if not bills:
            issues.append({"level": "warning", "code": "no_bills", "message": "No active recurring bills are configured."})
        missing_bill_dates = sum(1 for row in bills if not row.due_at)
        if missing_bill_dates:
            issues.append({"level": "error", "code": "bill_dates", "message": f"{missing_bill_dates} active bill(s) have no due date."})
        missing_payday_dates = sum(1 for row in paydays if not row.pay_at)
        if missing_payday_dates:
            issues.append({"level": "error", "code": "payday_dates", "message": f"{missing_payday_dates} active income source(s) have no pay date."})
        percentage_total = sum(
            (
                Decimal(row.allocation_value)
                for row in buckets
                if row.allocation_method == BudgetBucket.AllocationMethod.PERCENTAGE
            ),
            Decimal("0.00"),
        )
        if percentage_total > Decimal("100.00"):
            issues.append({"level": "error", "code": "allocation_over", "message": f"Percentage bucket rules total {percentage_total:.2f}%."})
        elif buckets and percentage_total == 0 and not any(
            row.allocation_method == BudgetBucket.AllocationMethod.FIXED for row in buckets
        ):
            issues.append({"level": "warning", "code": "allocation_empty", "message": "Active buckets do not allocate any income."})
        for bill in bills:
            ensure_bill_occurrences(bill, today - timedelta(days=365), today)
        overdue = selectors.list_bill_occurrences(
            request.user,
            start=today - timedelta(days=365),
            end=today,
            status="upcoming",
        )
        overdue = [row for row in overdue if row.is_overdue]
        if overdue:
            issues.append({"level": "error", "code": "overdue_bills", "message": f"{len(overdue)} bill occurrence(s) are overdue."})
        latest_balance = selectors.get_latest_balance(request.user)
        if latest_balance is None:
            issues.append({"level": "warning", "code": "no_balance", "message": "Add an account balance to enable projections."})
        elif (today - latest_balance.snapshot_date).days > 14:
            issues.append({"level": "warning", "code": "stale_balance", "message": f"The latest account balance is {(today - latest_balance.snapshot_date).days} days old."})
        return Response(
            {
                "status": (
                    "error" if any(row["level"] == "error" for row in issues)
                    else "warning" if issues else "healthy"
                ),
                "issues": issues,
                "counts": {
                    "active_bills": len(bills),
                    "active_paydays": len(paydays),
                    "active_buckets": len(buckets),
                    "overdue_occurrences": len(overdue),
                },
                "percentage_allocation_total": f"{percentage_total:.2f}",
                "latest_balance": (
                    AccountBalanceSnapshotSerializer(latest_balance).data
                    if latest_balance else None
                ),
            }
        )


class CategoryReportView(SolaceAccessMixin, APIView):
    def get(self, request: Request) -> Response:
        from apps.solace.bill_schedule import annual_cost, fortnightly_cost

        grouped = {}
        for bill in selectors.list_bills(request.user, active_only=True):
            row = grouped.setdefault(
                bill.category or "other",
                {
                    "category": bill.category or "other",
                    "bill_count": 0,
                    "annual_total": Decimal("0.00"),
                    "fortnightly_total": Decimal("0.00"),
                },
            )
            row["bill_count"] += 1
            if bill.include_in_set_aside:
                row["annual_total"] += annual_cost(bill)
                row["fortnightly_total"] += fortnightly_cost(bill)
        rows = [
            {
                **row,
                "annual_total": f"{row['annual_total']:.2f}",
                "fortnightly_total": f"{row['fortnightly_total']:.2f}",
            }
            for row in sorted(grouped.values(), key=lambda value: value["category"].lower())
        ]
        return Response(
            {
                "categories": rows,
                "annual_total": f"{sum((Decimal(row['annual_total']) for row in rows), Decimal('0.00')):.2f}",
                "fortnightly_total": f"{sum((Decimal(row['fortnightly_total']) for row in rows), Decimal('0.00')):.2f}",
            }
        )


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
            generated = ensure_bill_occurrences(
                bill,
                today - timedelta(days=365),
                today + timedelta(days=550),
            )
            bill.upcoming_occurrences = [
                row for row in generated if row.status == row.Status.UPCOMING
            ]
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


class SolaceBootstrapView(SolaceAccessMixin, APIView):
    """Load the finance workspace in one request to keep navigation responsive."""

    def get(self, request: Request) -> Response:
        return Response(
            {
                "bills": BillListView().get(request).data,
                "paydays": PaydayListView().get(request).data,
                "purchases": PurchaseListView().get(request).data,
                "buckets": BucketListView().get(request).data,
                "subscriptions": SubscriptionListView().get(request).data,
                "checklist": ChecklistListView().get(request).data,
                "plan": PayCyclePlanView().get(request).data,
                "settings": SolaceSettingsView().get(request).data,
                "categories": FinanceCategoryListView().get(request).data,
                "balances": AccountBalanceListView().get(request).data,
                "health": SolaceHealthView().get(request).data,
                "category_report": CategoryReportView().get(request).data,
                "closeout": CycleCloseoutView().get(request).data,
                "checklist_preferences": ChecklistPreferenceView().get(request).data,
            }
        )


class SolaceCsvExportView(SolaceAccessMixin, APIView):
    def get(self, request: Request, export_type: str) -> HttpResponse:
        from apps.solace.data_tools import (
            bill_rows,
            bucket_rows,
            csv_bytes,
            income_rows,
            purchase_rows,
        )

        exports = {
            "bills": ("solace-bills.csv", bill_rows),
            "purchases": ("solace-planned-purchases.csv", purchase_rows),
            "income": ("solace-income-sources.csv", income_rows),
            "buckets": ("solace-buckets.csv", bucket_rows),
        }
        selected = exports.get(export_type)
        if selected is None:
            raise NotFound()
        filename, builder = selected
        response = HttpResponse(csv_bytes(builder(request.user)), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class SolaceXlsxExportView(SolaceAccessMixin, APIView):
    def get(self, request: Request) -> HttpResponse:
        from apps.solace.data_tools import xlsx_bytes

        response = HttpResponse(
            xlsx_bytes(request.user),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="solace-readable-backup.xlsx"'
        return response


class BillImportPreviewView(SolaceAccessMixin, APIView):
    permission_action = "create"
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request: Request) -> Response:
        from apps.solace.data_tools import parse_bill_import_rows, read_uploaded_rows

        upload = request.FILES.get("file")
        if upload is None:
            raise ValidationError({"file": "Choose a CSV or XLSX file."})
        if upload.size > 5 * 1024 * 1024:
            raise ValidationError({"file": "Files cannot exceed 5 MB."})
        try:
            raw_rows = read_uploaded_rows(upload)
        except (UnicodeDecodeError, ValueError) as exc:
            raise ValidationError({"file": str(exc)}) from exc
        if len(raw_rows) > 1000:
            raise ValidationError({"file": "Imports cannot exceed 1,000 rows."})
        rows, error_count = parse_bill_import_rows(raw_rows)
        request._request.session["solace_bill_import_preview"] = rows
        return Response(
            {
                "rows": rows,
                "row_count": len(rows),
                "error_count": error_count,
                "ready_count": len(rows) - error_count,
            }
        )


class BillImportConfirmView(SolaceAccessMixin, APIView):
    permission_action = "create"

    def post(self, request: Request) -> Response:
        rows = request._request.session.get("solace_bill_import_preview") or []
        if not rows:
            raise ValidationError({"detail": "No bill import preview is waiting for confirmation."})
        validated = []
        errors = []
        for row in rows:
            if row.get("errors"):
                continue
            payload = {
                key: value
                for key, value in row.items()
                if key not in {"source_row", "errors"}
            }
            serializer = BillSerializer(data=payload)
            if serializer.is_valid():
                validated.append(serializer.validated_data)
            else:
                errors.append({"source_row": row.get("source_row"), "errors": serializer.errors})
        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            for payload in validated:
                from apps.solace.models import FinanceCategory

                category_name = payload.get("category") or "other"
                category = FinanceCategory.objects.filter(name__iexact=category_name).first()
                if category is None:
                    services.create_category(
                        request.user,
                        name=category_name,
                        category_type="bill",
                        position=(len(selectors.list_categories(request.user)) + 1) * 10,
                    )
                elif category.category_type == FinanceCategory.CategoryType.PURCHASE:
                    services.update_category(
                        request.user,
                        category,
                        category_type=FinanceCategory.CategoryType.BOTH,
                    )
                services.create_bill(request.user, **payload)
        skipped = len(rows) - len(validated)
        request._request.session.pop("solace_bill_import_preview", None)
        return Response({"imported_count": len(validated), "skipped_count": skipped})


class BillImportCancelView(SolaceAccessMixin, APIView):
    permission_action = "create"

    def post(self, request: Request) -> Response:
        request._request.session.pop("solace_bill_import_preview", None)
        return Response(status=status.HTTP_204_NO_CONTENT)
