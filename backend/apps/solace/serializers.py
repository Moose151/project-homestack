"""solace serializers."""
from __future__ import annotations

from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.solace.models import (
    AccountBalanceSnapshot,
    Bill,
    BillOccurrence,
    BudgetBucket,
    CycleCloseout,
    FinanceCategory,
    Payday,
    PaydayChecklistItem,
    PaydayChecklistPreference,
    PlannedPurchase,
    SolaceSettings,
    Subscription,
)


def _non_blank(value: str) -> str:
    if not value.strip():
        raise serializers.ValidationError("This field may not be blank.")
    return value


class BillSerializer(serializers.ModelSerializer):
    home_destination = serializers.ChoiceField(
        choices=("insurance_policy", "household_cost", "maintenance"),
        required=False,
        allow_blank=True,
        write_only=True,
    )
    is_overdue = serializers.SerializerMethodField()
    next_due_at = serializers.SerializerMethodField()
    next_occurrence_id = serializers.SerializerMethodField()
    annual_amount = serializers.SerializerMethodField()
    fortnightly_amount = serializers.SerializerMethodField()

    class Meta:
        model = Bill
        fields = [
            "id", "name", "category", "provider", "amount", "due_at", "is_all_day",
            "recurrence_rule", "end_date", "is_paid", "paid_at", "notes", "is_overdue",
            "is_active", "is_autopay", "include_in_set_aside",
            "next_due_at", "next_occurrence_id",
            "annual_amount", "fortnightly_amount",
            "source_node", "source_record_type", "source_record_id",
            "home_destination",
            "calendar_event_id", "visibility", "sensitivity", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "is_overdue", "next_due_at", "next_occurrence_id",
            "annual_amount", "fortnightly_amount",
            "source_node", "source_record_type", "source_record_id",
            "calendar_event_id", "created_at", "updated_at",
        ]

    def validate_name(self, value: str) -> str:
        return _non_blank(value)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        due_at = attrs.get("due_at", getattr(self.instance, "due_at", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if due_at and end_date and timezone.localdate(due_at) > end_date:
            raise serializers.ValidationError(
                {"end_date": "Stop-after date must be on or after the first due date."}
            )
        return attrs

    def get_next_due_at(self, obj):
        occurrence = self._next_occurrence(obj)
        return occurrence.due_at if occurrence else None

    def get_next_occurrence_id(self, obj):
        occurrence = self._next_occurrence(obj)
        return occurrence.id if occurrence else None

    def get_is_overdue(self, obj):
        occurrence = self._next_occurrence(obj)
        if occurrence:
            return occurrence.is_overdue
        return bool(
            obj.due_at
            and not obj.recurrence_rule
            and not obj.is_paid
            and obj.due_at < timezone.now()
        )

    @staticmethod
    def _next_occurrence(obj):
        prefetched = getattr(obj, "upcoming_occurrences", None)
        if prefetched is not None:
            return prefetched[0] if prefetched else None
        cached = getattr(obj, "_solace_next_occurrence", None)
        if cached is None and not hasattr(obj, "_solace_next_occurrence"):
            cached = obj.occurrences.filter(status=BillOccurrence.Status.UPCOMING).first()
            obj._solace_next_occurrence = cached
        return cached

    def get_annual_amount(self, obj):
        from apps.solace.bill_schedule import annual_cost

        return f"{annual_cost(obj):.2f}"

    def get_fortnightly_amount(self, obj):
        from apps.solace.bill_schedule import fortnightly_cost

        return f"{fortnightly_cost(obj):.2f}"


class BillOccurrenceSerializer(serializers.ModelSerializer):
    bill_id = serializers.IntegerField(read_only=True)
    bill_name = serializers.CharField(source="bill.name", read_only=True)
    bill_category = serializers.CharField(source="bill.category", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = BillOccurrence
        fields = [
            "id", "bill_id", "bill_name", "bill_category", "due_at", "amount",
            "status", "paid_at", "notes", "is_overdue", "visibility", "sensitivity",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class PaydaySerializer(serializers.ModelSerializer):
    next_pay_at = serializers.SerializerMethodField()

    class Meta:
        model = Payday
        fields = [
            "id", "title", "expected_amount", "pay_at", "is_all_day", "recurrence_rule",
            "next_pay_at", "received_at", "is_active", "notes", "calendar_event_id",
            "visibility", "sensitivity",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "next_pay_at", "calendar_event_id", "created_at", "updated_at",
        ]

    def validate_title(self, value: str) -> str:
        return _non_blank(value)

    def get_next_pay_at(self, obj: Payday):
        if not obj.is_active or not obj.pay_at:
            return None
        anchor = obj.pay_at
        if timezone.is_naive(anchor):
            anchor = timezone.make_aware(anchor, timezone.get_current_timezone())
        now = timezone.now()
        if not obj.recurrence_rule:
            return anchor if anchor >= now else None
        try:
            from dateutil.rrule import rrulestr

            return rrulestr(obj.recurrence_rule, dtstart=anchor).after(now, inc=True)
        except (TypeError, ValueError):
            return anchor if anchor >= now else None


class PlannedPurchaseSerializer(serializers.ModelSerializer):
    remaining_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    progress_percent = serializers.IntegerField(read_only=True)
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = PlannedPurchase
        fields = [
            "id", "name", "category", "target_amount", "saved_amount", "remaining_amount",
            "progress_percent", "target_date", "is_all_day", "status", "priority",
            "notes", "is_open", "calendar_event_id", "visibility", "sensitivity",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "remaining_amount", "progress_percent", "is_open", "calendar_event_id",
            "created_at", "updated_at",
        ]

    def validate_name(self, value: str) -> str:
        return _non_blank(value)


class PurchaseSavingsSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )


class BudgetBucketSerializer(serializers.ModelSerializer):
    remaining_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    progress_percent = serializers.IntegerField(read_only=True)

    class Meta:
        model = BudgetBucket
        fields = [
            "id", "name", "category", "target_amount", "current_amount",
            "remaining_amount", "progress_percent", "allocation_method", "allocation_value",
            "rounding_increment", "cap_to_remaining", "is_active", "position",
            "notes", "visibility", "sensitivity", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "remaining_amount", "progress_percent", "created_at", "updated_at",
        ]

    def validate_name(self, value: str) -> str:
        return _non_blank(value)

    def validate_allocation_value(self, value):
        if value < 0:
            raise serializers.ValidationError("Allocation value cannot be negative.")
        return value

    def validate_rounding_increment(self, value):
        if value <= 0:
            raise serializers.ValidationError("Rounding increment must be greater than zero.")
        return value


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = [
            "id", "name", "provider", "amount", "billing_cycle", "next_renewal_at",
            "is_all_day", "recurrence_rule", "is_active", "notes", "calendar_event_id",
            "visibility", "sensitivity", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "calendar_event_id", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        return _non_blank(value)


class PaydayChecklistItemSerializer(serializers.ModelSerializer):
    bucket_id = serializers.IntegerField(required=False, allow_null=True)
    bill_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = PaydayChecklistItem
        fields = [
            "id", "title", "cycle_start", "source_key", "bucket_id", "bill_id",
            "amount_hint", "position", "is_complete", "completed_at",
            "notes", "visibility", "sensitivity",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "cycle_start", "source_key", "completed_at", "created_at", "updated_at",
        ]

    def validate_title(self, value: str) -> str:
        return _non_blank(value)


class SolaceSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolaceSettings
        fields = [
            "id", "currency_symbol", "budget_year", "cycle_anchor_date",
            "default_buffer_amount",
            "payday_bill_handling", "show_help_tips", "dashboard_reminders",
            "due_soon_days", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_currency_symbol(self, value: str) -> str:
        return _non_blank(value)

    def validate_budget_year(self, value):
        if value is not None and not 2000 <= value <= 2200:
            raise serializers.ValidationError("Budget year must be between 2000 and 2200.")
        return value

    def validate_due_soon_days(self, value):
        if not 1 <= value <= 60:
            raise serializers.ValidationError("Due-soon days must be between 1 and 60.")
        return value


class FinanceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FinanceCategory
        fields = [
            "id", "name", "category_type", "is_active", "position",
            "visibility", "sensitivity", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        value = _non_blank(value)
        qs = FinanceCategory.objects.filter(name__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A category with this name already exists.")
        return value


class AccountBalanceSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountBalanceSnapshot
        fields = [
            "id", "snapshot_date", "balance", "notes", "visibility",
            "sensitivity", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PaydayChecklistPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaydayChecklistPreference
        fields = [
            "id", "source_key", "label", "is_hidden", "reason",
            "visibility", "sensitivity", "created_at", "updated_at",
        ]
        read_only_fields = fields


class CycleCloseoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = CycleCloseout
        fields = [
            "id", "cycle_start", "cycle_end", "status", "closed_at", "notes",
            "visibility", "sensitivity", "created_at", "updated_at",
        ]
        read_only_fields = fields
