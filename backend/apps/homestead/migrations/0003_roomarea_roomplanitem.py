# Generated for HomeStack Homestead room planning (v0.18.0).
import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("homestead", "0002_householdcost_insurancepolicy"),
        ("people", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RoomArea",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("name", models.CharField(max_length=160)),
                ("area_type", models.CharField(choices=[("interior", "Interior room"), ("outdoor", "Outdoor area"), ("utility", "Utility / service area"), ("storage", "Storage"), ("other", "Other")], default="interior", max_length=20)),
                ("description", models.TextField(blank=True, default="")),
                ("icon", models.CharField(blank=True, default="", max_length=50)),
                ("colour", models.CharField(blank=True, default="#B0563C", max_length=20)),
                ("display_order", models.PositiveSmallIntegerField(default=0)),
                ("floorplan_data", models.JSONField(blank=True, default=dict)),
                ("visibility", models.CharField(choices=[("private", "Private"), ("household", "Household"), ("role_restricted", "Role Restricted"), ("sensitive", "Sensitive")], default="household", max_length=20)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("household", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="+", to="core.household")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "room or area", "ordering": ["display_order", "name", "id"]},
        ),
        migrations.CreateModel(
            name="RoomPlanItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("title", models.CharField(max_length=255)),
                ("item_type", models.CharField(choices=[("purchase", "Purchase"), ("maintenance", "Maintenance"), ("renovation", "Renovation"), ("upgrade", "Upgrade")], default="purchase", max_length=20)),
                ("status", models.CharField(choices=[("planned", "Planned"), ("in_progress", "In progress"), ("completed", "Completed"), ("archived", "Archived")], default="planned", max_length=20)),
                ("priority", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")], default="medium", max_length=10)),
                ("description", models.TextField(blank=True, default="")),
                ("quantity", models.DecimalField(decimal_places=2, default=Decimal("1.00"), max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))])),
                ("estimated_unit_cost", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal("0.00"))])),
                ("actual_cost", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, validators=[django.core.validators.MinValueValidator(Decimal("0.00"))])),
                ("link_url", models.CharField(blank=True, default="", max_length=500)),
                ("notes", models.TextField(blank=True, default="")),
                ("position", models.PositiveSmallIntegerField(default=0)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("visibility", models.CharField(choices=[("private", "Private"), ("household", "Household"), ("role_restricted", "Role Restricted"), ("sensitive", "Sensitive")], default="household", max_length=20)),
                ("assigned_to_person", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="people.person")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("household", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="+", to="core.household")),
                ("room", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="plan_items", to="homestead.roomarea")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "room plan item", "ordering": ["position", "-updated_at", "id"]},
        ),
    ]
