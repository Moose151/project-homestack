from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.atlas.models import AtlasList, AtlasListItem, AtlasListSuggestion
from apps.core.models import Household
from apps.people.models import Person


class PersonalListSuggestionTests(TestCase):
    def setUp(self):
        household = Household.objects.first() or Household.objects.create(name="List home", slug="list-home", timezone="Australia/Brisbane")
        self.owner_user = User.objects.create_user("list_owner", "Owner", password="pw", role=User.Role.USER)
        self.other_user = User.objects.create_user("list_other", "Other", password="pw", role=User.Role.USER)
        self.owner = Person.objects.create(household=household, linked_user=self.owner_user, display_name="Owner", created_by=self.owner_user, updated_by=self.owner_user)
        self.other = Person.objects.create(household=household, linked_user=self.other_user, display_name="Other", created_by=self.owner_user, updated_by=self.owner_user)
        self.wishes = AtlasList.objects.create(
            household=household, title="Owner's wishes", list_type="wishlist", owner_person=self.owner,
            visibility="household", created_by=self.owner_user, updated_by=self.owner_user,
        )

    def test_other_member_suggests_and_owner_accepts_without_direct_edit(self):
        self.client.force_login(self.other_user)
        response = self.client.post(
            reverse("atlas-list-suggestion-list", args=[self.wishes.id]),
            {"title": "Desk lamp", "product_url": "https://example.com/lamp", "unit_price": "49.00"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        suggestion_id = response.json()["id"]
        self.assertEqual(AtlasListItem.objects.count(), 0)
        self.client.force_login(self.owner_user)
        response = self.client.post(
            reverse("atlas-list-suggestion-review", args=[self.wishes.id, suggestion_id, "accept"]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "accepted")
        item = AtlasListItem.objects.get()
        self.assertEqual(item.title, "Desk lamp")
        self.assertEqual(list(item.assigned_to_people.values_list("id", flat=True)), [self.owner.id])

    def test_other_member_cannot_accept_suggestion(self):
        suggestion = AtlasListSuggestion.objects.create(
            household=self.wishes.household, atlas_list=self.wishes, suggested_by_person=self.other,
            title="Chair", created_by=self.other_user, updated_by=self.other_user,
        )
        self.client.force_login(self.other_user)
        response = self.client.post(
            reverse("atlas-list-suggestion-review", args=[self.wishes.id, suggestion.id, "accept"]),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(AtlasListItem.objects.count(), 0)

    def test_other_member_cannot_edit_personal_list_directly(self):
        self.client.force_login(self.other_user)
        response = self.client.post(
            reverse("atlas-list-item-list", args=[self.wishes.id]),
            {"title": "Sneaky direct item"}, content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(AtlasListItem.objects.count(), 0)

    def test_private_personal_list_is_not_disclosed_through_suggestions(self):
        self.wishes.visibility = "private"
        self.wishes.save(update_fields=["visibility", "updated_at"])
        self.client.force_login(self.other_user)
        response = self.client.post(
            reverse("atlas-list-suggestion-list", args=[self.wishes.id]),
            {"title": "Hidden"}, content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
