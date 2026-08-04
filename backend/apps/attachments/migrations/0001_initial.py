# Generated for HomeStack Milestone 4 attachment security.
import apps.attachments.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("core", "0004_household_calendar_default_view_and_more"),
        ("nodes", "0006_configure_solace_sensitive"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Attachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("filename", models.CharField(max_length=255)),
                ("original_filename", models.CharField(max_length=255)),
                ("file_path", models.FileField(max_length=500, upload_to=apps.attachments.models.attachment_upload_path)),
                ("mime_type", models.CharField(blank=True, default="application/octet-stream", max_length=255)),
                ("file_size", models.PositiveBigIntegerField()),
                ("checksum", models.CharField(max_length=64)),
                ("linked_record_type", models.CharField(blank=True, default="", max_length=150)),
                ("linked_record_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("visibility", models.CharField(choices=[("private", "Private"), ("household", "Household"), ("role_restricted", "Role restricted"), ("sensitive", "Sensitive")], default="household", max_length=20)),
                ("sensitivity", models.CharField(choices=[("normal", "Normal"), ("financial", "Financial"), ("health", "Health"), ("document", "Document"), ("private", "Private")], default="normal", max_length=20)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("household", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="+", to="core.household")),
                ("linked_node", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="attachments", to="nodes.node")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("uploaded_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="uploaded_attachments", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddIndex(
            model_name="attachment",
            index=models.Index(fields=["household", "linked_record_type", "linked_record_id"], name="attachment_link_idx"),
        ),
    ]
