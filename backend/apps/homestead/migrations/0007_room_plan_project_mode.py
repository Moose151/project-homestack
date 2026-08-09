"""Room jobs can be projects: parts that are all required, whose prices sum.

Owner request, 2026-08-09. A job's products were always *alternatives* — three sofas, pick
one, that price is the estimate. A project is the opposite: desk + monitor + chair are all
needed, so the estimate is their total. `plan_mode` decides which arithmetic applies; the rows
and the add-form are the same either way.

Parts also carry `is_purchased` and the price actually paid, so a project reads
"3 of 5 bought · $700 spent, $250 to go". Existing jobs stay `single`, which is what they were.
"""
import django.core.validators
from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('homestead', '0006_multi_person_assignment'),
    ]

    operations = [
        migrations.AddField(
            model_name='roomplanitem',
            name='plan_mode',
            field=models.CharField(choices=[('single', 'Single item'), ('project', 'Project')], default='single', help_text='single: products are alternatives. project: products are parts that sum.', max_length=10),
        ),
        migrations.AddField(
            model_name='roomplanproduct',
            name='actual_cost',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Total actually paid for this part, if it differed from the estimate.', max_digits=12, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))]),
        ),
        migrations.AddField(
            model_name='roomplanproduct',
            name='is_purchased',
            field=models.BooleanField(default=False, help_text='Project parts: already bought.'),
        ),
        migrations.AlterField(
            model_name='roomplanproduct',
            name='is_chosen',
            field=models.BooleanField(default=False, help_text='Single-item jobs only: the alternative picked, whose price is the estimate.'),
        ),
    ]
