from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("atlas", "0007_atlaslistitem_priority"), ("people", "0002_cornerreaction_and_more")]
    operations = [
        migrations.AddField(
            model_name="atlasreminder",
            name="assigned_to_people",
            field=models.ManyToManyField(
                blank=True,
                help_text="Who should receive this reminder. Empty means the whole household.",
                related_name="assigned_reminders",
                to="people.person",
            ),
        ),
        migrations.AddField(
            model_name="atlasreminder",
            name="notifications_enabled",
            field=models.BooleanField(
                default=True,
                help_text="Allow the shared notification scheduler to notify recipients for this reminder.",
            ),
        ),
    ]
