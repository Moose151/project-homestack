"""solace serializers."""
from __future__ import annotations

from rest_framework import serializers

from apps.solace.models import (
    Bill,
    BillOccurrence,
    BudgetBucket,
    Payday,
    PaydayChecklistItem,
    PlannedPurchase,
    Subscription,
)


def _non_blank(value: str) -> str:
    if not value.strip():
        raise serializers.ValidationError("This field may not be blank.")
    return value


class BillSerializer(serializers.ModelSerializer):
    is_overdue = serializers.BooleanField(read_only=True)
    next_due_at = serializers.SerializerMethodField()
    next_occurrence_id = serializers.SerializerMethodField()
    annual_amount = serializers.SerializerMethodField()
    fortnightly_amount = serializers.SerializerMethodField()

    class Meta:
        model = Bill
        fields = [
            "id", "name", "category", "provider", "amount", "due_at", "is_all_day",
            "recurrence_rule", "is_paid", "paid_at", "notes", "is_overdue",
            "is_active", "include_in_set_aside", "next_due_at", "next_occurrence_id",
            "annual_amount", "fortnightly_amount",
            "source_node", "source_record_type", "source_record_id",
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

    def get_next_due_at(self, obj):
        occurrence = obj.occurrences.filter(status=BillOccurrence.Status.UPCOMING).first()
        return occurrence.due_at if occurrence else None

    def get_next_occurrence_id(self, obj):
        occurrence = obj.occurrences.filter(status=BillOccurrence.Status.UPCOMING).first()
        return occurrence.id if occurrence else None

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
    class Meta:
        model = Payday
        fields = [
            "id", "title", "expected_amount", "pay_at", "is_all_day", "recurrence_rule",
            "received_at", "is_active", "notes", "calendar_event_id", "visibility", "sensitivity",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "calendar_event_id", "created_at", "updated_at"]

    def validate_title(self, value: str) -> str:
        return _non_blank(value)


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
