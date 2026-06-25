"""Seed the notifications.view permission (Milestone 2, Phase 2.15).

Every authenticated role may read and manage **their own** notifications (the views scope to
the requesting user). There is no cross-user notification access, so a single view grant covers
list + mark-read (which resolve as self-service `view` actions).
"""
from django.db import migrations

_CODE = "notifications.view"
_NAME = "View own notifications"
_ROLES = ["admin", "manager", "user", "guest"]


def seed_forward(apps, schema_editor):
    Permission = apps.get_model("permissions", "Permission")
    Role = apps.get_model("permissions", "Role")
    RolePermission = apps.get_model("permissions", "RolePermission")

    perm, _ = Permission.objects.get_or_create(
        code=_CODE, defaults={"name": _NAME, "scope": "notifications"}
    )
    for role_name in _ROLES:
        try:
            role = Role.objects.get(name=role_name)
        except Role.DoesNotExist:
            continue
        RolePermission.objects.get_or_create(role=role, permission=perm)


def seed_reverse(apps, schema_editor):
    Permission = apps.get_model("permissions", "Permission")
    Permission.objects.filter(code=_CODE).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("permissions", "0010_seed_achievements_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
