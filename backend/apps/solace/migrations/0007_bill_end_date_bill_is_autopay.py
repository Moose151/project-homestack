from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("solace", "0006_solacesettings_dashboard_reminders_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="bill",
            name="end_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="bill",
            name="is_autopay",
            field=models.BooleanField(default=False),
        ),
    ]
