"""Seed the meridian.contribute permission (Milestone 2, Phases 2.12/2.13).

Contributing points to group goals and wishlist items is a child-safe action (listed in the
resolver's _CHILD_SAFE_ACTIONS): admins, managers and users (incl. children) may contribute;
guests may not. All other writes remain blocked for children.
"""
from django.db import migrations

_CODE = "meridian.contribute"
_NAME = "Contribute points to Meridian goals/wishlist"
_ROLES = ["admin", "manager", "user"]


def seed_forward(apps, schema_editor):
    Permission = apps.get_model("permissions", "Permission")
    Role = apps.get_model("permissions", "Role")
    RolePermission = apps.get_model("permissions", "RolePermission")

    perm, _ = Permission.objects.get_or_create(
        code=_CODE, defaults={"name": _NAME, "scope": "meridian"}
    )
    for role_name in _ROLES:
        try:
            role = Role.objects.get(name=role_name)
        except Role.DoesNotExist:
            continue
        RolePermission.objects.get_or_create(role=role, permission=perm)


def seed_reverse(apps, schema_editor):
    Permission = apps.get_model("permissions", "Permission")
    Permission.objects.filter(code=_CODE).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("permissions", "0008_seed_meridian_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
