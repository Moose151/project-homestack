"""Seed Homestead permissions (Node Spec 25).

homestead.view   — all roles
homestead.create — admin, manager, user
homestead.edit   — admin, manager, user
homestead.delete — admin, manager

Finer visibility (sensitive/restricted records hidden from children/guests) is enforced by the
central resolver + apply_visibility, not by extra permission codes.
"""
from django.db import migrations

_PERMISSIONS = [
    {"code": "homestead.view",   "name": "View Homestead content",   "scope": "homestead"},
    {"code": "homestead.create", "name": "Create Homestead content", "scope": "homestead"},
    {"code": "homestead.edit",   "name": "Edit Homestead content",   "scope": "homestead"},
    {"code": "homestead.delete", "name": "Delete Homestead content", "scope": "homestead"},
]

_ROLE_GRANTS = {
    "admin":   ["homestead.view", "homestead.create", "homestead.edit", "homestead.delete"],
    "manager": ["homestead.view", "homestead.create", "homestead.edit", "homestead.delete"],
    "user":    ["homestead.view", "homestead.create", "homestead.edit"],
    "guest":   ["homestead.view"],
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
        ("permissions", "0017_seed_pets_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
