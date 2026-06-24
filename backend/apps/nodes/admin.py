from django.contrib import admin

from apps.nodes.models import HouseholdNode, Node, NodeSetting


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ["key", "name", "is_core", "is_enabled_by_default", "supports_kiosk"]
    search_fields = ["key", "name"]


@admin.register(HouseholdNode)
class HouseholdNodeAdmin(admin.ModelAdmin):
    list_display = ["node", "is_enabled", "display_order", "custom_name"]
    list_filter = ["is_enabled"]


@admin.register(NodeSetting)
class NodeSettingAdmin(admin.ModelAdmin):
    list_display = ["node", "key", "value_json"]
