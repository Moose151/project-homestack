import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="GuideDismissal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("guide_identifier", models.CharField(max_length=100)),
                ("guide_version", models.CharField(default="1", max_length=50)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("household", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="+", to="core.household")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="guide_dismissals", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["guide_identifier", "guide_version"]},
        ),
        migrations.AddConstraint(
            model_name="guidedismissal",
            constraint=models.UniqueConstraint(fields=("user", "guide_identifier", "guide_version"), name="unique_user_guide_version_dismissal"),
        ),
    ]
