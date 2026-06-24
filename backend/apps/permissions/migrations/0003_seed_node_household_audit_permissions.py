"""
Seed permissions for nodes, household, and audit log access.

nodes.view    — everyone: list the node registry
nodes.edit    — admin: enable/disable nodes, update node settings
household.view — everyone: read the household record
household.edit — admin: update household name/timezone/locale
audit.view    — admin: read audit logs
"""
from django.db import migrations

_NEW_PERMISSIONS = [
    {"code": "nodes.view",     "name": "View nodes",        "scope": "nodes"},
    {"code": "nodes.edit",     "name": "Manage nodes",      "scope": "nodes"},
    {"code": "household.view", "name": "View household",    "scope": "household"},
    {"code": "household.edit", "name": "Edit household",    "scope": "household"},
    {"code": "audit.view",     "name": "View audit logs",   "scope": "audit"},
]

_ROLE_GRANTS = {
    "admin":   ["nodes.view", "nodes.edit", "household.view", "household.edit", "audit.view"],
    "manager": ["nodes.view", "household.view"],
    "user":    ["nodes.view", "household.view"],
    "guest":   ["nodes.view", "household.view"],
}


def seed_forward(apps, schema_editor):
    Permission = apps.get_model("permissions", "Permission")
    Role = apps.get_model("permissions", "Role")
    RolePermission = apps.get_model("permissions", "RolePermission")

    perm_map = {}
    for p in _NEW_PERMISSIONS:
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
    Permission.objects.filter(code__in=[p["code"] for p in _NEW_PERMISSIONS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("permissions", "0002_seed_roles_and_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
