"""Multi-person assignment: replace the single assignee FK with a people M2M.

Owner request, 2026-08-09. An assignment was one `assigned_to_person` where null meant "the
whole household", which could not express "both of us". `assigned_to_people` is now the set:
empty means the whole household, one or more people means each of them.

Existing single assignees are copied into the new relation before the old column is dropped,
so nothing loses its owner.
"""
from django.db import migrations, models


_MODELS = ['meridiantask', 'meridianroutine']


def carry_assignees_forward(apps, schema_editor):
    for model_name in _MODELS:
        Model = apps.get_model("meridian", model_name)
        for row in Model.objects.exclude(assigned_to_person__isnull=True).iterator():
            row.assigned_to_people.set([row.assigned_to_person_id])


def carry_assignees_back(apps, schema_editor):
    """Restore a sole assignee. A record assigned to several people cannot round-trip."""
    for model_name in _MODELS:
        Model = apps.get_model("meridian", model_name)
        for row in Model.objects.iterator():
            ids = list(row.assigned_to_people.values_list("id", flat=True))
            if len(ids) == 1:
                row.assigned_to_person_id = ids[0]
                row.save(update_fields=["assigned_to_person"])


class Migration(migrations.Migration):
    dependencies = [
        ("meridian", "0012_meridianreward_category"),
        ("people", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="meridiantask",
            name="assigned_to_people",
            field=models.ManyToManyField(
                blank=True,
                help_text=(
                    "Who this is for. Empty means anyone in the household may do it. "
                    "Several people means each of them, not one of them."
                ),
                related_name="assigned_meridian_tasks",
                to="people.person",
            ),
        ),
        migrations.AddField(
            model_name="meridianroutine",
            name="assigned_to_people",
            field=models.ManyToManyField(
                blank=True,
                help_text=(
                    "If set, only these people see/complete the routine; empty = everyone."
                ),
                related_name="assigned_meridian_routines",
                to="people.person",
            ),
        ),

        migrations.RunPython(carry_assignees_forward, carry_assignees_back),
        migrations.RemoveField(model_name="meridiantask", name="assigned_to_person"),
        migrations.RemoveField(model_name="meridianroutine", name="assigned_to_person"),

    ]
