from django.db import migrations


def subscriptions_to_bills(apps, schema_editor):
    Bill = apps.get_model("solace", "Bill")
    Subscription = apps.get_model("solace", "Subscription")
    CalendarEvent = apps.get_model("scheduling", "CalendarEvent")

    for subscription in Subscription.objects.filter(deleted_at__isnull=True).iterator():
        bill = Bill.objects.create(
            household_id=subscription.household_id,
            created_by_id=subscription.created_by_id,
            updated_by_id=subscription.updated_by_id,
            name=subscription.name,
            category="subscription",
            provider=subscription.provider,
            amount=subscription.amount,
            due_at=subscription.next_renewal_at,
            is_all_day=subscription.is_all_day,
            recurrence_rule=subscription.recurrence_rule,
            is_active=subscription.is_active,
            is_autopay=False,
            include_in_set_aside=True,
            notes=subscription.notes,
            calendar_event_id=subscription.calendar_event_id,
            visibility=subscription.visibility,
            sensitivity=subscription.sensitivity,
        )
        Bill.objects.filter(pk=bill.pk).update(
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
        )
        if subscription.calendar_event_id:
            CalendarEvent.objects.filter(pk=subscription.calendar_event_id).update(
                title=f"Bill: {subscription.name}",
                source_record_type="Bill",
                source_record_id=bill.pk,
                colour="#8f4e38",
            )


class Migration(migrations.Migration):
    dependencies = [
        ("scheduling", "0003_multi_person_assignment"),
        ("solace", "0009_income_scope_and_allocations"),
    ]

    operations = [
        migrations.RunPython(subscriptions_to_bills, migrations.RunPython.noop),
        migrations.DeleteModel(name="Subscription"),
    ]
