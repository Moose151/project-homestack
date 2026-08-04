"""Seed shared attachment permissions with child safety enforced by the resolver."""
from django.db import migrations


PERMISSIONS = [
    ("attachments.view", "View attachments"),
    ("attachments.create", "Upload attachments"),
    ("attachments.edit", "Edit attachment metadata"),
    ("attachments.delete", "Delete attachments"),
]

GRANTS = {
    "admin": [code for code, _name in PERMISSIONS],
    "manager": [code for code, _name in PERMISSIONS],
    "user": ["attachments.view", "attachments.create", "attachments.delete"],
    "guest": ["attachments.view"],
}


def seed_permissions(apps, schema_editor):
    Permission = apps.get_model("permissions", "Permission")
    Role = apps.get_model("permissions", "Role")
    RolePermission = apps.get_model("permissions", "RolePermission")
    permission_map = {}
    for code, name in PERMISSIONS:
        permission, _created = Permission.objects.get_or_create(
            code=code,
            defaults={"name": name, "scope": "attachments"},
        )
        permission_map[code] = permission
    for role_name, codes in GRANTS.items():
        role = Role.objects.get(name=role_name)
        for code in codes:
            RolePermission.objects.get_or_create(role=role, permission=permission_map[code])


def unseed_permissions(apps, schema_editor):
    Permission = apps.get_model("permissions", "Permission")
    Permission.objects.filter(code__in=[code for code, _name in PERMISSIONS]).delete()


class Migration(migrations.Migration):
    dependencies = [("permissions", "0019_seed_solace_permissions")]
    operations = [migrations.RunPython(seed_permissions, unseed_permissions)]
