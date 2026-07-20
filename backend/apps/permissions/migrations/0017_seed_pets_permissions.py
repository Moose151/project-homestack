"""Seed Pets permissions (Node Spec 7).

pets.view   — all roles
pets.create — admin, manager, user
pets.edit   — admin, manager, user  (users may complete permitted pet-care actions)
pets.delete — admin, manager

Finer visibility (sensitive/restricted records hidden from children/guests) is enforced by the
central resolver + apply_visibility, not by extra permission codes.
"""
from django.db import migrations

_PERMISSIONS = [
    {"code": "pets.view",   "name": "View Pets content",   "scope": "pets"},
    {"code": "pets.create", "name": "Create Pets content", "scope": "pets"},
    {"code": "pets.edit",   "name": "Edit Pets content",   "scope": "pets"},
    {"code": "pets.delete", "name": "Delete Pets content", "scope": "pets"},
]

_ROLE_GRANTS = {
    "admin":   ["pets.view", "pets.create", "pets.edit", "pets.delete"],
    "manager": ["pets.view", "pets.create", "pets.edit", "pets.delete"],
    "user":    ["pets.view", "pets.create", "pets.edit"],
    "guest":   ["pets.view"],
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
        ("permissions", "0016_seed_home_wiki_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
