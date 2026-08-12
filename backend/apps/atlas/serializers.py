"""atlas serializers."""
from __future__ import annotations

from rest_framework import serializers

from apps.core.serializers import AssigneeSerializerMixin

from apps.atlas.models import AtlasContact, AtlasList, AtlasListItem, AtlasListSuggestion, AtlasNote, AtlasReminder


class AtlasNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AtlasNote
        fields = [
            "id", "title", "body", "visibility", "sensitivity",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_title(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Title may not be blank.")
        return value


class AtlasListItemSerializer(AssigneeSerializerMixin, serializers.ModelSerializer):
    is_complete = serializers.BooleanField(read_only=True)
    cached_image_url = serializers.SerializerMethodField()
    price_watch = serializers.SerializerMethodField()
    cache_image = serializers.BooleanField(write_only=True, required=False)
    price_watch_enabled = serializers.BooleanField(write_only=True, required=False)

    class Meta:
        model = AtlasListItem
        fields = [
            "id", "atlas_list_id", "title", "notes", "quantity", "priority", "position", "due_at", "calendar_event_id",
            "product_url", "source_image_url", "cached_image_url", "image_attachment_id",
            "retailer", "unit_price", "currency", "imported_at",
            "price_watch", "cache_image", "price_watch_enabled",
            "assigned_to_person_ids",
            "completed_at", "completed_by_id", "is_complete",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "atlas_list_id", "calendar_event_id", "cached_image_url", "image_attachment_id", "imported_at", "price_watch", "completed_at", "completed_by_id", "is_complete", "created_at", "updated_at"]

    def get_cached_image_url(self, obj):
        return f"/api/v1/attachments/{obj.image_attachment_id}/download/" if obj.image_attachment_id else ""

    def get_price_watch(self, obj):
        from apps.link_imports.models import LinkWatch
        from apps.link_imports.services import serialize_watch
        return serialize_watch(LinkWatch.objects.filter(
            source_node="atlas", source_record_type="AtlasListItem", source_record_id=obj.id,
        ).first())


class AtlasListSerializer(serializers.ModelSerializer):
    items = AtlasListItemSerializer(many=True, read_only=True)

    class Meta:
        model = AtlasList
        fields = [
            "id", "title", "list_type", "visibility", "owner_person_id",
            "items", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "items", "created_at", "updated_at"]

    def validate_title(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Title may not be blank.")
        return value


class AtlasListWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AtlasList
        fields = ["title", "list_type", "visibility", "owner_person"]

    def validate_title(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Title may not be blank.")
        return value


class AtlasListItemWriteSerializer(AssigneeSerializerMixin, serializers.ModelSerializer):
    cache_image = serializers.BooleanField(write_only=True, required=False)
    price_watch_enabled = serializers.BooleanField(write_only=True, required=False)
    class Meta:
        model = AtlasListItem
        fields = [
            "title", "notes", "quantity", "priority", "position", "due_at", "assigned_to_person_ids",
            "product_url", "source_image_url", "retailer", "unit_price", "currency",
            "cache_image", "price_watch_enabled",
        ]

    def validate_title(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Title may not be blank.")
        return value


class AtlasListSuggestionSerializer(serializers.ModelSerializer):
    suggested_by_name = serializers.CharField(source="suggested_by_person.name", read_only=True)

    class Meta:
        model = AtlasListSuggestion
        fields = [
            "id", "atlas_list_id", "suggested_by_person_id", "suggested_by_name", "title",
            "notes", "product_url", "source_image_url", "retailer", "unit_price", "currency",
            "status", "accepted_item_id", "created_at", "reviewed_at",
        ]
        read_only_fields = [
            "id", "atlas_list_id", "suggested_by_person_id", "suggested_by_name", "status",
            "accepted_item_id", "created_at", "reviewed_at",
        ]

    def validate_title(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Title may not be blank.")
        return value


class AtlasReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = AtlasReminder
        fields = [
            "id", "title", "body", "due_at", "is_all_day", "recurrence_rule",
            "calendar_event_id", "visibility", "sensitivity",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "calendar_event_id", "created_at", "updated_at"]

    def validate_title(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Title may not be blank.")
        return value


class AtlasContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = AtlasContact
        fields = ["id", "name", "date_of_birth", "relationship", "notes", "linked_person_id", "visibility", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Name may not be blank.")
        return value.strip()
