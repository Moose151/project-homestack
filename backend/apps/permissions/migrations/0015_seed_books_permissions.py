"""Seed Books permissions."""
from django.db import migrations

_PERMISSIONS = [
    {"code": "books.view", "name": "View Books content", "scope": "books"},
    {"code": "books.create", "name": "Create Books content", "scope": "books"},
    {"code": "books.edit", "name": "Edit Books content", "scope": "books"},
    {"code": "books.delete", "name": "Delete Books content", "scope": "books"},
]

_ROLE_GRANTS = {
    "admin": ["books.view", "books.create", "books.edit", "books.delete"],
    "manager": ["books.view", "books.create", "books.edit", "books.delete"],
    "user": ["books.view", "books.create", "books.edit"],
    "guest": ["books.view"],
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
        ("permissions", "0014_seed_education_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
