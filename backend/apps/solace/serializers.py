"""solace serializers."""
from __future__ import annotations

from rest_framework import serializers

from apps.solace.models import (
    Bill,
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

    class Meta:
        model = Bill
        fields = [
            "id", "name", "category", "provider", "amount", "due_at", "is_all_day",
            "recurrence_rule", "is_paid", "paid_at", "notes", "is_overdue",
            "source_node", "source_record_type", "source_record_id",
            "calendar_event_id", "visibility", "sensitivity", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "is_overdue", "source_node", "source_record_type", "source_record_id",
            "calendar_event_id", "created_at", "updated_at",
        ]

    def validate_name(self, value: str) -> str:
        return _non_blank(value)


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
