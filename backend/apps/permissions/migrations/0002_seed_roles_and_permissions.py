"""
Seed the four system roles (admin, manager, user, guest) and initial permissions
for People, then assign default role_permissions.

Permission matrix seeded here:
  admin   → people.view / .create / .edit / .delete
  manager → people.view / .create / .edit / .delete
  user    → people.view
  guest   → people.view

Additional scopes (atlas.*, scheduling.*, …) will be added in their respective phases.
Extend this or create a new data migration when new node permissions are needed.
"""
from django.db import migrations

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

_PERMISSIONS = [
    {"code": "people.view",   "name": "View people",   "scope": "people"},
    {"code": "people.create", "name": "Create people", "scope": "people"},
    {"code": "people.edit",   "name": "Edit people",   "scope": "people"},
    {"code": "people.delete", "name": "Delete people", "scope": "people"},
]

_ROLE_PERMISSIONS = {
    "admin":   ["people.view", "people.create", "people.edit", "people.delete"],
    "manager": ["people.view", "people.create", "people.edit", "people.delete"],
    "user":    ["people.view"],
    "guest":   ["people.view"],
}


def seed_forward(apps, schema_editor):
    Household = apps.get_model("core", "Household")
    Role = apps.get_model("permissions", "Role")
    Permission = apps.get_model("permissions", "Permission")
    RolePermission = apps.get_model("permissions", "RolePermission")

    household = Household.objects.order_by("id").first()
    if not household:
        return  # no household yet (shouldn't happen in normal flow)

    # Create permission catalogue entries
    perm_map = {}
    for p in _PERMISSIONS:
        obj, _ = Permission.objects.get_or_create(
            code=p["code"],
            defaults={"name": p["name"], "scope": p["scope"]},
        )
        perm_map[p["code"]] = obj

    # Create system roles and wire up default permissions
    for role_name, codes in _ROLE_PERMISSIONS.items():
        role, _ = Role.objects.get_or_create(
            household=household,
            name=role_name,
            defaults={"description": f"System role: {role_name}", "is_system_role": True},
        )
        for code in codes:
            RolePermission.objects.get_or_create(role=role, permission=perm_map[code])


def seed_reverse(apps, schema_editor):
    Role = apps.get_model("permissions", "Role")
    Permission = apps.get_model("permissions", "Permission")
    Role.objects.filter(is_system_role=True).delete()
    Permission.objects.filter(code__in=[p["code"] for p in _PERMISSIONS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("permissions", "0001_initial"),
        ("core", "0002_seed_household"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
