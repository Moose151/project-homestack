"""Seed Solace permissions.

Solace is financial/sensitive. Admin is granted by default; managers/users/guests are not.
Manager access can be granted deliberately via user permissions later.
"""
from django.db import migrations

_PERMS = [
    {"code": "solace.view", "name": "View Solace finance", "scope": "solace"},
    {"code": "solace.create", "name": "Create Solace finance", "scope": "solace"},
    {"code": "solace.edit", "name": "Edit Solace finance", "scope": "solace"},
    {"code": "solace.delete", "name": "Delete Solace finance", "scope": "solace"},
]


def seed_forward(apps, schema_editor):
    Permission = apps.get_model("permissions", "Permission")
    Role = apps.get_model("permissions", "Role")
    RolePermission = apps.get_model("permissions", "RolePermission")

    created = {}
    for data in _PERMS:
        perm, _ = Permission.objects.get_or_create(code=data["code"], defaults=data)
        created[data["code"]] = perm

    admin = Role.objects.filter(name="admin").first()
    if admin:
        for perm in created.values():
            RolePermission.objects.get_or_create(role=admin, permission=perm)


def seed_reverse(apps, schema_editor):
    Permission = apps.get_model("permissions", "Permission")
    Permission.objects.filter(code__in=[p["code"] for p in _PERMS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("permissions", "0018_seed_homestead_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
