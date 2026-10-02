from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("solace", "0011_remove_budgetbucket_category")]

    operations = [
        # Set-aside is a budgeting preference, not evidence of a different payment account.
        # Include existing bills by default; users can explicitly mark payments made elsewhere.
        migrations.AddField(
            model_name="bill",
            name="paid_from_bills_account",
            field=models.BooleanField(default=True),
        ),
    ]
