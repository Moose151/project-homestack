from django.contrib import admin

from apps.permissions.models import Permission, Role, RolePermission, UserPermission


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "scope"]
    search_fields = ["code", "name"]
    ordering = ["code"]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "is_system_role", "created_at"]
    list_filter = ["is_system_role"]


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ["role", "permission"]
    list_filter = ["role"]


@admin.register(UserPermission)
class UserPermissionAdmin(admin.ModelAdmin):
    list_display = ["user", "permission", "is_granted"]
    list_filter = ["is_granted"]
