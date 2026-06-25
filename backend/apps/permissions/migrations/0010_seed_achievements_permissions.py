"""Seed the achievements.view permission (Milestone 2, Phase 2.14).

Everyone can see badges (children love seeing what they've earned). Badges are awarded by the
event system, never via the API, so there is no create/edit/delete permission to grant.
"""
from django.db import migrations

_CODE = "achievements.view"
_NAME = "View achievement badges"
_ROLES = ["admin", "manager", "user", "guest"]


def seed_forward(apps, schema_editor):
    Permission = apps.get_model("permissions", "Permission")
    Role = apps.get_model("permissions", "Role")
    RolePermission = apps.get_model("permissions", "RolePermission")

    perm, _ = Permission.objects.get_or_create(
        code=_CODE, defaults={"name": _NAME, "scope": "achievements"}
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
        ("permissions", "0009_seed_meridian_contribute"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
