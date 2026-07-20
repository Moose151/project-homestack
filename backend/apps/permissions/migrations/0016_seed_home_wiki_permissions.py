"""Seed Home Wiki permissions (Node Spec 7).

homewiki.view   — all roles (children/guests still gated to safe pages by visibility + kiosk).
homewiki.create — admin, manager, user
homewiki.edit   — admin, manager, user
homewiki.delete — admin, manager

Finer visibility (private/sensitive pages hidden from children/guests) is enforced by the
central resolver + apply_visibility, not by extra permission codes.
"""
from django.db import migrations

_PERMISSIONS = [
    {"code": "homewiki.view",   "name": "View Home Wiki content",   "scope": "home_wiki"},
    {"code": "homewiki.create", "name": "Create Home Wiki content", "scope": "home_wiki"},
    {"code": "homewiki.edit",   "name": "Edit Home Wiki content",   "scope": "home_wiki"},
    {"code": "homewiki.delete", "name": "Delete Home Wiki content", "scope": "home_wiki"},
]

_ROLE_GRANTS = {
    "admin":   ["homewiki.view", "homewiki.create", "homewiki.edit", "homewiki.delete"],
    "manager": ["homewiki.view", "homewiki.create", "homewiki.edit", "homewiki.delete"],
    "user":    ["homewiki.view", "homewiki.create", "homewiki.edit"],
    "guest":   ["homewiki.view"],
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
        ("permissions", "0015_seed_books_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
