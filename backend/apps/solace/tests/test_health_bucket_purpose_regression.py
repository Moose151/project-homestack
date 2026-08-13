"""Regression coverage for Solace health checks after BudgetBucket.category removal."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.solace.models import BudgetBucket
from apps.solace.services import create_bill, create_bucket


class SolaceHealthBucketPurposeRegressionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            display_name="Admin",
            role=User.Role.ADMIN,
            password="pass123!",
        )
        self.admin.set_pin("1234")
        self.admin.save()
        self.client.post(
            reverse("auth-pin-login"),
            {"username": "admin", "pin": "1234"},
            content_type="application/json",
        )
        self.client.post(
            reverse("auth-reauth"),
            {"password": "pass123!"},
            content_type="application/json",
        )

    def test_health_and_bootstrap_use_bucket_purpose_not_removed_category(self):
        create_bill(
            self.admin,
            name="Electricity",
            category="utilities",
            amount="120.00",
            due_at=timezone.now() + timedelta(days=7),
            recurrence_rule="FREQ=MONTHLY",
        )
        create_bucket(
            self.admin,
            name="Bills",
            purpose=BudgetBucket.Purpose.BILLS,
            allocation_method=BudgetBucket.AllocationMethod.PERCENTAGE,
            allocation_value="50.00",
        )

        health = self.client.get(reverse("solace-health"))
        self.assertEqual(health.status_code, 200)
        self.assertNotIn(
            "no_bills_bucket",
            {row["code"] for row in health.json()["issues"]},
        )

        bootstrap = self.client.get(reverse("solace-bootstrap"))
        self.assertEqual(bootstrap.status_code, 200)
        self.assertIn("health", bootstrap.json())
