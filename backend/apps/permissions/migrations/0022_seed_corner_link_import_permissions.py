from django.db import migrations


PERMISSIONS = [
    ("corners.view", "View household Corners"),
    ("corners.react", "React to visible Corner activity"),
    ("link_imports.create", "Preview and watch public product links"),
    ("link_imports.view", "View product link watches"),
    ("link_imports.edit", "Edit product link watches"),
]
GRANTS = {
    "admin": [code for code, _ in PERMISSIONS],
    "manager": [code for code, _ in PERMISSIONS],
    "user": [code for code, _ in PERMISSIONS],
    "guest": ["corners.view", "link_imports.view"],
}


def seed(apps, schema_editor):
    Permission = apps.get_model("permissions", "Permission")
    Role = apps.get_model("permissions", "Role")
    RolePermission = apps.get_model("permissions", "RolePermission")
    for code, name in PERMISSIONS:
        permission, _ = Permission.objects.update_or_create(
            code=code, defaults={"name": name, "scope": code.split(".", 1)[0]}
        )
        for role_name, codes in GRANTS.items():
            if code in codes:
                for role in Role.objects.filter(name=role_name):
                    RolePermission.objects.get_or_create(role=role, permission=permission)


def unseed(apps, schema_editor):
    Permission = apps.get_model("permissions", "Permission")
    Permission.objects.filter(code__in=[code for code, _ in PERMISSIONS]).delete()


class Migration(migrations.Migration):
    dependencies = [("permissions", "0021_seed_fitness_permissions")]
    operations = [migrations.RunPython(seed, unseed)]
