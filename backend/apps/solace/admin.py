from django.contrib import admin

from apps.solace.models import (
    Bill,
    BillOccurrence,
    BudgetBucket,
    Payday,
    PaydayChecklistItem,
    PlannedPurchase,
    Subscription,
)

@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = (
        "name", "category", "amount", "due_at", "is_paid",
        "source_node", "source_record_type", "source_record_id",
    )
    search_fields = ("name", "provider", "notes")
    list_filter = ("category", "is_paid", "source_node")


admin.site.register(Payday)
admin.site.register(BillOccurrence)
admin.site.register(PlannedPurchase)
admin.site.register(BudgetBucket)
admin.site.register(Subscription)
admin.site.register(PaydayChecklistItem)
