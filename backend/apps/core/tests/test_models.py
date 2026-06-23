"""Phase 1.2 tests — Household tenant anchor and the seed (D1, D15).

Soft-delete / manager behaviour on HouseholdBaseModel is covered once the first concrete
subclass exists (accounts.User, Phase 1.3) — the abstract base's created_by/updated_by FKs
target AUTH_USER_MODEL, which has no table yet.
"""
from django.test import TestCase

from apps.core.models import Household, get_active_household


class HouseholdSeedTests(TestCase):
    def test_exactly_one_household_seeded(self):
        self.assertEqual(Household.objects.count(), 1)

    def test_get_active_household_returns_seeded_row(self):
        household = get_active_household()
        self.assertIsNotNone(household)
        self.assertEqual(household.slug, "homestack")
        self.assertEqual(household.timezone, "UTC")

    def test_household_str(self):
        self.assertEqual(str(get_active_household()), "HomeStack Household")
