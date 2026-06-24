"""Seed Meridian permissions (Milestone 2, Node Spec 7).

meridian.view     — all roles (children see their tasks/points/rewards)
meridian.create   — admin, manager   (define tasks, rewards, categories)
meridian.edit     — admin, manager
meridian.delete   — admin, manager
meridian.approve  — admin, manager   (approve/reject tasks and reward requests)
meridian.complete — admin, manager, user  (child-safe: complete a task)
meridian.request  — admin, manager, user  (child-safe: request a reward)

`complete` and `request` are also listed in the resolver's _CHILD_SAFE_ACTIONS, so a
child account (role=user) may perform them; all other writes remain blocked for children.
"""
from django.db import migrations

_PERMISSIONS = [
    {"code": "meridian.view",     "name": "View Meridian content",   "scope": "meridian"},
    {"code": "meridian.create",   "name": "Create Meridian content", "scope": "meridian"},
    {"code": "meridian.edit",     "name": "Edit Meridian content",   "scope": "meridian"},
    {"code": "meridian.delete",   "name": "Delete Meridian content", "scope": "meridian"},
    {"code": "meridian.approve",  "name": "Approve Meridian tasks/rewards", "scope": "meridian"},
    {"code": "meridian.complete", "name": "Complete a Meridian task", "scope": "meridian"},
    {"code": "meridian.request",  "name": "Request a Meridian reward", "scope": "meridian"},
]

_ROLE_GRANTS = {
    "admin":   ["meridian.view", "meridian.create", "meridian.edit", "meridian.delete",
                "meridian.approve", "meridian.complete", "meridian.request"],
    "manager": ["meridian.view", "meridian.create", "meridian.edit", "meridian.delete",
                "meridian.approve", "meridian.complete", "meridian.request"],
    "user":    ["meridian.view", "meridian.complete", "meridian.request"],
    "guest":   ["meridian.view"],
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
        ("permissions", "0007_seed_backup_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
