"""Seed Atlas permissions.

atlas.view   — all roles
atlas.create — admin, manager, user  (users can make their own notes/lists)
atlas.edit   — admin, manager, user
atlas.delete — admin, manager
"""
from django.db import migrations

_PERMISSIONS = [
    {"code": "atlas.view",   "name": "View Atlas content",   "scope": "atlas"},
    {"code": "atlas.create", "name": "Create Atlas content",  "scope": "atlas"},
    {"code": "atlas.edit",   "name": "Edit Atlas content",    "scope": "atlas"},
    {"code": "atlas.delete", "name": "Delete Atlas content",  "scope": "atlas"},
]

_ROLE_GRANTS = {
    "admin":   ["atlas.view", "atlas.create", "atlas.edit", "atlas.delete"],
    "manager": ["atlas.view", "atlas.create", "atlas.edit", "atlas.delete"],
    "user":    ["atlas.view", "atlas.create", "atlas.edit"],
    "guest":   ["atlas.view"],
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
        ("permissions", "0004_seed_scheduling_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
