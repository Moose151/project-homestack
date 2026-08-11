from rest_framework import serializers

from apps.link_imports.models import LinkWatch


class LinkPreviewSerializer(serializers.Serializer):
    url = serializers.URLField(max_length=1000)
    kind = serializers.ChoiceField(choices=["product"])


class LinkWatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = LinkWatch
        fields = [
            "id", "source_node", "source_record_type", "source_record_id", "owner_person_id",
            "url", "title", "retailer", "currency", "baseline_price", "current_price",
            "lowest_price", "rule", "threshold_percent", "target_price", "is_active",
            "last_checked_at", "last_succeeded_at", "consecutive_failures", "last_error",
        ]
        read_only_fields = [
            "id", "source_node", "source_record_type", "source_record_id", "owner_person_id",
            "url", "title", "retailer", "currency", "baseline_price", "current_price",
            "lowest_price", "last_checked_at", "last_succeeded_at", "consecutive_failures", "last_error",
        ]
