"""Seed scheduling permissions.

scheduling.view   — all roles
scheduling.create — admin, manager
scheduling.edit   — admin, manager
scheduling.delete — admin, manager
"""
from django.db import migrations

_PERMISSIONS = [
    {"code": "scheduling.view",   "name": "View calendar events",   "scope": "scheduling"},
    {"code": "scheduling.create", "name": "Create calendar events",  "scope": "scheduling"},
    {"code": "scheduling.edit",   "name": "Edit calendar events",    "scope": "scheduling"},
    {"code": "scheduling.delete", "name": "Delete calendar events",  "scope": "scheduling"},
]

_ROLE_GRANTS = {
    "admin":   ["scheduling.view", "scheduling.create", "scheduling.edit", "scheduling.delete"],
    "manager": ["scheduling.view", "scheduling.create", "scheduling.edit", "scheduling.delete"],
    "user":    ["scheduling.view"],
    "guest":   ["scheduling.view"],
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
        ("permissions", "0003_seed_node_household_audit_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
