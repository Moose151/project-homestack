from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("homestead", "0003_roomarea_roomplanitem"),
    ]

    operations = [
        migrations.AddField(
            model_name="maintenancetask",
            name="solace_bill_ref",
            field=models.PositiveBigIntegerField(blank=True, editable=False, null=True),
        ),
    ]
