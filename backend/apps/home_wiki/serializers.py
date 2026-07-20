"""home_wiki serializers."""
from __future__ import annotations

from rest_framework import serializers

from apps.home_wiki.models import WikiCategory, WikiPage


def _non_blank(value: str) -> str:
    if not value.strip():
        raise serializers.ValidationError("This field may not be blank.")
    return value


class WikiCategorySerializer(serializers.ModelSerializer):
    page_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = WikiCategory
        fields = [
            "id", "name", "colour", "icon", "display_order", "is_hidden",
            "page_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "page_count", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        return _non_blank(value)


class WikiPageSerializer(serializers.ModelSerializer):
    # DRF treats a bare `<fk>_id` in `fields` as read-only; declare it so writes land.
    category_id = serializers.IntegerField(required=False, allow_null=True)
    category_name = serializers.CharField(source="category.name", read_only=True, default="")
    category_colour = serializers.CharField(source="category.colour", read_only=True, default="")
    tag_list = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = WikiPage
        fields = [
            "id", "title", "body", "category_id", "category_name", "category_colour",
            "tags", "tag_list", "is_favourite", "is_emergency", "is_kiosk_safe",
            "visibility", "sensitivity", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "category_name", "category_colour", "tag_list", "created_at", "updated_at",
        ]

    def validate_title(self, value: str) -> str:
        return _non_blank(value)
