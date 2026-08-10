from django.db import migrations


PERMISSIONS = [
    ("fitness.view", "View fitness activity"),
    ("fitness.create", "Create fitness programs and workouts"),
    ("fitness.edit", "Edit fitness programs and workouts"),
    ("fitness.delete", "Delete fitness programs and exercises"),
]
GRANTS = {
    "admin": [code for code, _ in PERMISSIONS],
    "manager": [code for code, _ in PERMISSIONS],
    "user": ["fitness.view", "fitness.create", "fitness.edit"],
    "guest": ["fitness.view"],
}


def seed_forward(apps, schema_editor):
    Permission = apps.get_model("permissions", "Permission")
    Role = apps.get_model("permissions", "Role")
    RolePermission = apps.get_model("permissions", "RolePermission")
    permission_map = {}
    for code, name in PERMISSIONS:
        permission_map[code], _ = Permission.objects.get_or_create(code=code, defaults={"name": name, "scope": "fitness"})
    for role_name, codes in GRANTS.items():
        role = Role.objects.filter(name=role_name).first()
        if role:
            for code in codes:
                RolePermission.objects.get_or_create(role=role, permission=permission_map[code])


def seed_reverse(apps, schema_editor):
    apps.get_model("permissions", "Permission").objects.filter(code__in=[code for code, _ in PERMISSIONS]).delete()


class Migration(migrations.Migration):
    dependencies = [("permissions", "0020_seed_attachment_permissions")]
    operations = [migrations.RunPython(seed_forward, seed_reverse)]

