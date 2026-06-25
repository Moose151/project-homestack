"""Seed user-management permissions (admin-only).

Managing login accounts + roles is sensitive, so only the admin role is granted these. Other
roles get nothing here, so the central resolver denies them user management.
"""
from django.db import migrations

_PERMISSIONS = [
    {"code": "users.view", "name": "View user accounts", "scope": "users"},
    {"code": "users.create", "name": "Create user accounts", "scope": "users"},
    {"code": "users.edit", "name": "Edit user accounts", "scope": "users"},
    {"code": "users.delete", "name": "Deactivate user accounts", "scope": "users"},
]


def seed_forward(apps, schema_editor):
    Permission = apps.get_model("permissions", "Permission")
    Role = apps.get_model("permissions", "Role")
    RolePermission = apps.get_model("permissions", "RolePermission")

    try:
        admin = Role.objects.get(name="admin")
    except Role.DoesNotExist:
        admin = None
    for p in _PERMISSIONS:
        perm, _ = Permission.objects.get_or_create(
            code=p["code"], defaults={"name": p["name"], "scope": p["scope"]}
        )
        if admin:
            RolePermission.objects.get_or_create(role=admin, permission=perm)


def seed_reverse(apps, schema_editor):
    Permission = apps.get_model("permissions", "Permission")
    Permission.objects.filter(code__in=[p["code"] for p in _PERMISSIONS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("permissions", "0011_seed_notifications_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
