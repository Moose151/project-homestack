"""Seed Education permissions (Node Spec 7).

education.view   — all roles
education.create — admin, manager, user  (adults manage their own uni records)
education.edit   — admin, manager, user
education.delete — admin, manager

Finer relationship-based visibility (children see only their own school items; adults keep
university records private/household) is enforced by the central resolver + apply_visibility,
not by extra permission codes.
"""
from django.db import migrations

_PERMISSIONS = [
    {"code": "education.view",   "name": "View Education content",   "scope": "education"},
    {"code": "education.create", "name": "Create Education content", "scope": "education"},
    {"code": "education.edit",   "name": "Edit Education content",   "scope": "education"},
    {"code": "education.delete", "name": "Delete Education content", "scope": "education"},
]

_ROLE_GRANTS = {
    "admin":   ["education.view", "education.create", "education.edit", "education.delete"],
    "manager": ["education.view", "education.create", "education.edit", "education.delete"],
    "user":    ["education.view", "education.create", "education.edit"],
    "guest":   ["education.view"],
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
        ("permissions", "0013_seed_hub_edit_permission"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
