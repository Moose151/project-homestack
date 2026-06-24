"""Seed backup permissions.

backups.view    — admin only: list and download backups
backups.create  — admin only: trigger a backup (also needs re-auth in view)
backups.restore — admin only: restore a backup (also needs re-auth in view)
"""
from django.db import migrations

_PERMISSIONS = [
    {"code": "backups.view",    "name": "View backups",    "scope": "backups"},
    {"code": "backups.create",  "name": "Create backups",  "scope": "backups"},
    {"code": "backups.restore", "name": "Restore backups", "scope": "backups"},
]

_ROLE_GRANTS = {
    "admin": ["backups.view", "backups.create", "backups.restore"],
}


def seed_forward(apps, schema_editor):
    Permission = apps.get_model("permissions", "Permission")
    Role = apps.get_model("permissions", "Role")
    RolePermission = apps.get_model("permissions", "RolePermission")

    perm_map = {}
    for p in _PERMISSIONS:
        obj, _ = Permission.objects.get_or_create(
            code=p["code"], defaults={"name": p["name"], "scope": p["scope"]}
        )
        perm_map[p["code"]] = obj

    for role_name, codes in _ROLE_GRANTS.items():
        try:
            role = Role.objects.get(name=role_name)
        except Role.DoesNotExist:
            continue
        for code in codes:
            RolePermission.objects.get_or_create(role=role, permission=perm_map[code])


def seed_reverse(apps, schema_editor):
    Permission = apps.get_model("permissions", "Permission")
    Permission.objects.filter(code__in=[p["code"] for p in _PERMISSIONS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("permissions", "0006_seed_hub_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
