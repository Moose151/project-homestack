from django.db import migrations


PERMISSIONS = [("travel.view", "View travel plans"), ("travel.create", "Create travel plans"), ("travel.edit", "Edit travel plans"), ("travel.delete", "Delete travel plans")]
GRANTS = {"admin": [code for code, _ in PERMISSIONS], "manager": [code for code, _ in PERMISSIONS], "user": ["travel.view", "travel.create", "travel.edit"], "guest": ["travel.view"]}


def seed(apps, schema_editor):
    Permission = apps.get_model("permissions", "Permission")
    RolePermission = apps.get_model("permissions", "RolePermission")
    Role = apps.get_model("permissions", "Role")
    for code, name in PERMISSIONS:
        permission, _ = Permission.objects.get_or_create(code=code, defaults={"name": name, "scope": "travel"})
        for role_name, codes in GRANTS.items():
            if code in codes:
                role = Role.objects.filter(name=role_name).first()
                if role:
                    RolePermission.objects.get_or_create(role=role, permission=permission)


def unseed(apps, schema_editor):
    apps.get_model("permissions", "Permission").objects.filter(code__in=[code for code, _ in PERMISSIONS]).delete()


class Migration(migrations.Migration):
    dependencies = [("permissions", "0022_seed_corner_link_import_permissions")]
    operations = [migrations.RunPython(seed, unseed)]
