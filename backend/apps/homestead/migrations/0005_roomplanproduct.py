"""Replace a room plan item's single `link_url` with a shopping list of options.

Owner request, 2026-08-09: a room job could hold one link, which cannot answer "which of the
three sofas were we looking at?". Each `RoomPlanProduct` is one candidate purchase — what it
is, where to buy it, what it costs and a picture — and the option marked `is_chosen` drives
the plan item's estimate.

Images are URLs rather than uploads so adding an option is a copy-paste from a retailer page.

Existing `link_url` values are carried into a product row named after their plan item so no
link is lost, then the field is dropped: two places to store a link is how they drift apart.
"""
import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


def carry_links_forward(apps, schema_editor):
    RoomPlanItem = apps.get_model("homestead", "RoomPlanItem")
    RoomPlanProduct = apps.get_model("homestead", "RoomPlanProduct")

    # Historical models expose a plain manager, which is what we want here: soft-deleted
    # items keep their link too, so an undelete does not silently lose it.
    for item in RoomPlanItem.objects.exclude(link_url="").iterator():
        RoomPlanProduct.objects.create(
            household_id=item.household_id,
            plan_item=item,
            title=item.title,
            url=item.link_url,
            quantity=item.quantity,
            unit_cost=item.estimated_unit_cost,
            is_chosen=True,
            position=0,
            created_by_id=item.created_by_id,
            updated_by_id=item.updated_by_id,
        )


def carry_links_back(apps, schema_editor):
    RoomPlanProduct = apps.get_model("homestead", "RoomPlanProduct")
    for product in RoomPlanProduct.objects.filter(is_chosen=True).select_related("plan_item"):
        if product.url and not product.plan_item.link_url:
            product.plan_item.link_url = product.url
            product.plan_item.save(update_fields=["link_url"])


class Migration(migrations.Migration):
    dependencies = [
        ("homestead", "0004_maintenancetask_solace_bill_ref"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RoomPlanProduct",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("title", models.CharField(max_length=255)),
                ("url", models.CharField(blank=True, default="", max_length=500)),
                ("image_url", models.CharField(blank=True, default="", max_length=500)),
                ("retailer", models.CharField(blank=True, default="", max_length=120)),
                ("quantity", models.DecimalField(decimal_places=2, default=Decimal("1.00"), max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))])),
                ("unit_cost", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal("0.00"))])),
                ("is_chosen", models.BooleanField(default=False)),
                ("notes", models.TextField(blank=True, default="")),
                ("position", models.PositiveSmallIntegerField(default=0)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("household", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="+", to="core.household")),
                ("plan_item", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="products", to="homestead.roomplanitem")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "room plan product",
                "ordering": ["position", "id"],
            },
        ),
        migrations.RunPython(carry_links_forward, carry_links_back),
        migrations.RemoveField(model_name="roomplanitem", name="link_url"),
    ]
