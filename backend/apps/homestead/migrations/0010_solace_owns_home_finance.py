from django.db import migrations


RRULES = {
    "weekly": "FREQ=WEEKLY",
    "fortnightly": "FREQ=WEEKLY;INTERVAL=2",
    "monthly": "FREQ=MONTHLY",
    "quarterly": "FREQ=MONTHLY;INTERVAL=3",
    "half_yearly": "FREQ=MONTHLY;INTERVAL=6",
    "yearly": "FREQ=YEARLY",
}


def move_home_finance_to_solace(apps, schema_editor):
    Bill = apps.get_model("solace", "Bill")
    InsurancePolicy = apps.get_model("homestead", "InsurancePolicy")
    HouseholdCost = apps.get_model("homestead", "HouseholdCost")

    def find_bill(record, record_type):
        bill = None
        if record.solace_bill_ref:
            bill = Bill.objects.filter(
                pk=record.solace_bill_ref, household_id=record.household_id
            ).first()
        if bill is None:
            bill = Bill.objects.filter(
                household_id=record.household_id,
                source_node="homestead",
                source_record_type=record_type,
                source_record_id=record.id,
            ).order_by("-updated_at").first()
        return bill

    def save_bill(record, record_type, values):
        bill = find_bill(record, record_type)
        if bill is None:
            bill = Bill(
                household_id=record.household_id,
                created_by_id=record.created_by_id,
                updated_by_id=record.updated_by_id,
            )
        for field, value in values.items():
            setattr(bill, field, value)
        bill.deleted_at = None
        # This link controls where the bill is displayed; Solace remains its write owner.
        bill.source_node = "homestead"
        bill.source_record_type = record_type
        bill.source_record_id = record.id
        bill.visibility = "sensitive"
        bill.sensitivity = "financial"
        bill.save()
        record.solace_bill_ref = bill.id
        record.save(update_fields=["solace_bill_ref"])

    for policy in InsurancePolicy.objects.all().iterator():
        save_bill(policy, "insurance_policy", {
            "name": policy.name,
            "category": "insurance",
            "provider": policy.provider,
            "amount": policy.premium_amount,
            "due_at": policy.next_renewal_at,
            "is_all_day": True,
            "recurrence_rule": policy.recurrence_rule or RRULES.get(policy.billing_cycle, ""),
            "is_active": policy.is_active,
            "notes": policy.notes,
        })

    categories = {"rates": "council", "mortgage": "mortgage"}
    for cost in HouseholdCost.objects.all().iterator():
        save_bill(cost, "household_cost", {
            "name": cost.name,
            "category": categories.get(cost.cost_type, "utilities"),
            "provider": cost.provider,
            "amount": cost.amount,
            "due_at": cost.next_due_at,
            "is_all_day": True,
            "recurrence_rule": cost.recurrence_rule or RRULES.get(cost.billing_cycle, ""),
            "is_active": cost.is_active,
            "notes": cost.notes,
        })


class Migration(migrations.Migration):
    dependencies = [
        ("homestead", "0009_utility_bills"),
        ("solace", "0010_consolidate_subscriptions_into_bills"),
    ]

    operations = [migrations.RunPython(move_home_finance_to_solace, migrations.RunPython.noop)]
