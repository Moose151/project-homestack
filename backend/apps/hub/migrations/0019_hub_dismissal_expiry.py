from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    """Snoozes expire instead of hiding a row forever.

    Any row already present becomes immediately expired: the table ships in the same
    unreleased release as this change, and failing open (the row is visible again) is the
    safe direction for a feature whose whole risk is silently hiding something.
    """

    dependencies = [
        ("hub", "0018_hubupcomingdismissal"),
    ]

    operations = [
        migrations.AddField(
            model_name="hubupcomingdismissal",
            name="hidden_until",
            field=models.DateTimeField(default=timezone.now),
            preserve_default=False,
        ),
    ]
