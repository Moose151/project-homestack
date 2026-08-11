from django.db import models

from apps.core.models import AllObjectsManager, HouseholdBaseModel, HouseholdManager


class LinkWatch(HouseholdBaseModel):
    class Rule(models.TextChoices):
        MEANINGFUL_DROP = "meaningful_drop", "Meaningful price drop"
        EXPLICIT_SALE = "explicit_sale", "Marked on sale"
        TARGET = "target", "At or below target"

    source_node = models.CharField(max_length=40)
    source_record_type = models.CharField(max_length=80)
    source_record_id = models.PositiveBigIntegerField()
    owner_person = models.ForeignKey(
        "people.Person", on_delete=models.CASCADE, related_name="link_watches"
    )
    url = models.CharField(max_length=1000)
    title = models.CharField(max_length=255)
    retailer = models.CharField(max_length=160, blank=True, default="")
    currency = models.CharField(max_length=3, default="AUD")
    baseline_price = models.DecimalField(max_digits=12, decimal_places=2)
    current_price = models.DecimalField(max_digits=12, decimal_places=2)
    lowest_price = models.DecimalField(max_digits=12, decimal_places=2)
    rule = models.CharField(max_length=24, choices=Rule.choices, default=Rule.MEANINGFUL_DROP)
    threshold_percent = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    target_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_succeeded_at = models.DateTimeField(null=True, blank=True)
    last_notified_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    consecutive_failures = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=255, blank=True, default="")

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["title", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["household", "source_node", "source_record_type", "source_record_id", "owner_person"],
                name="link_imports_unique_watch_source_owner",
            )
        ]


class PriceObservation(HouseholdBaseModel):
    watch = models.ForeignKey(LinkWatch, on_delete=models.CASCADE, related_name="observations")
    observed_at = models.DateTimeField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    list_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_sale = models.BooleanField(default=False)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["-observed_at", "-id"]
