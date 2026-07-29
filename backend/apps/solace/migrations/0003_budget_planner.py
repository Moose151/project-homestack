from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("solace", "0002_bill_source_node_bill_source_record_id_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="budgetbucket",
            name="allocation_method",
            field=models.CharField(
                choices=[
                    ("percentage", "Percentage of pay"),
                    ("fixed", "Fixed household amount"),
                ],
                default="percentage",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="budgetbucket",
            name="allocation_value",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=10,
            ),
        ),
        migrations.AddField(
            model_name="payday",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="budgetbucket",
            name="cap_to_remaining",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="budgetbucket",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="budgetbucket",
            name="position",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="budgetbucket",
            name="rounding_increment",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("1.00"),
                max_digits=8,
            ),
        ),
        migrations.AddField(
            model_name="paydaychecklistitem",
            name="cycle_start",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="paydaychecklistitem",
            name="source_key",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AlterModelOptions(
            name="budgetbucket",
            options={"ordering": ["position", "name"]},
        ),
        migrations.AlterModelOptions(
            name="paydaychecklistitem",
            options={"ordering": ["-cycle_start", "is_complete", "position", "title"]},
        ),
        migrations.AddConstraint(
            model_name="paydaychecklistitem",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ("deleted_at__isnull", True),
                    ("cycle_start__isnull", False),
                    models.Q(("source_key", ""), _negated=True),
                ),
                fields=("household", "cycle_start", "source_key"),
                name="unique_active_solace_cycle_checklist_source",
            ),
        ),
    ]
