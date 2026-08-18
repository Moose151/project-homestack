from __future__ import annotations

from rest_framework import serializers

from apps.quicklaunch.models import QuickLaunchShortcut


class QuickLaunchShortcutSerializer(serializers.ModelSerializer):
    """One shortcut as the client sees it.

    `id` is the public UUID, never the database key: the row id is not something a client needs
    and exposing it would invite guessing at other people's rows.
    """

    id = serializers.UUIDField(source="public_id", read_only=True)
    label = serializers.SerializerMethodField()
    icon = serializers.SerializerMethodField()
    node_key = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    unavailable_reason = serializers.SerializerMethodField()

    class Meta:
        model = QuickLaunchShortcut
        fields = [
            "id", "target_key", "target_object_id", "custom_label", "label", "icon",
            "node_key", "launch_mode", "display_order", "status", "unavailable_reason",
        ]
        read_only_fields = fields

    def _resolution(self, obj):
        cache = self.context.setdefault("_resolutions", {})
        if obj.pk not in cache:
            from apps.quicklaunch.registry import resolve
            cache[obj.pk] = resolve(obj, self.context["user"], self.context.get("request_obj"))
        return cache[obj.pk]

    def get_label(self, obj) -> str:
        return self._resolution(obj).label or obj.custom_label or obj.target_key

    def get_icon(self, obj) -> str:
        from apps.quicklaunch.registry import REGISTRY
        target = REGISTRY.get(obj.target_key)
        return target.icon if target else "◇"

    def get_node_key(self, obj) -> str:
        from apps.quicklaunch.registry import REGISTRY
        target = REGISTRY.get(obj.target_key)
        return target.node_key if target else ""

    def get_status(self, obj) -> str:
        # "ok" | "locked" | "unavailable" — the list itself never carries the route, so a
        # locked or unavailable shortcut discloses nothing about where it would have gone.
        return self._resolution(obj).status

    def get_unavailable_reason(self, obj) -> str:
        resolution = self._resolution(obj)
        return "" if resolution.ok else resolution.reason


class QuickLaunchShortcutWriteSerializer(serializers.Serializer):
    target_key = serializers.CharField(max_length=64)
    target_object_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    custom_label = serializers.CharField(max_length=60, required=False, allow_blank=True)
    launch_mode = serializers.ChoiceField(
        choices=QuickLaunchShortcut.LaunchMode.choices, required=False,
    )


class QuickLaunchShortcutUpdateSerializer(serializers.Serializer):
    custom_label = serializers.CharField(max_length=60, required=False, allow_blank=True)
    launch_mode = serializers.ChoiceField(
        choices=QuickLaunchShortcut.LaunchMode.choices, required=False,
    )


class QuickLaunchReorderSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.UUIDField(), max_length=50)
