"""Drop BudgetBucket.category, promoting any bucket that relied on it first.

`category` was free text sitting next to `purpose` and saying almost the same thing. The bucket
form never populated it, but bills forecasting decided "does this bucket fund the bills account?"
by looking for the substring "bill" in it — so a household's projected pay came out as zero.

Forward: any bucket whose old category said "bill" but whose purpose was never set is promoted to
purpose=bills, so a household that happened to type the right word keeps the behaviour it had.
"""
from django.db import migrations


def promote_bills_category_to_purpose(apps, schema_editor):
    BudgetBucket = apps.get_model("solace", "BudgetBucket")
    BudgetBucket.objects.filter(category__icontains="bill", purpose="other").update(purpose="bills")


def restore_category_from_purpose(apps, schema_editor):
    """Reverse: put the word back so a rolled-back forecast still finds its bills bucket."""
    BudgetBucket = apps.get_model("solace", "BudgetBucket")
    BudgetBucket.objects.filter(purpose="bills").update(category="bills")


class Migration(migrations.Migration):

    dependencies = [
        ("solace", "0010_consolidate_subscriptions_into_bills"),
    ]

    operations = [
        # On reverse Django re-adds the (empty) column first, then runs this — so rolling back
        # restores the word the old forecast needed rather than leaving it silently broken.
        migrations.RunPython(promote_bills_category_to_purpose, restore_category_from_purpose),
        migrations.RemoveField(
            model_name="budgetbucket",
            name="category",
        ),
    ]
