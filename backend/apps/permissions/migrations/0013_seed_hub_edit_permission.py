"""Seed the Hub edit permission (M2.5 Workstream A — widget configuration).

hub.edit — admin + manager may configure household-level Hub widgets (enable/disable,
order, size). Per-user overrides (hide/reorder one's own Hub) are gated by hub.view, since
any member may arrange their own Hub.
"""
from django.db import migrations

_PERMISSIONS = [
    {"code": "hub.edit", "name": "Configure hub widgets", "scope": "hub"},
]

_ROLE_GRANTS = {
    "admin":   ["hub.edit"],
    "manager": ["hub.edit"],
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
        ("permissions", "0012_seed_users_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
