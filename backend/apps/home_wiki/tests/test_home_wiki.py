"""Home Wiki tests — Milestone 3 V1 slice. Permission tests first (D10).

Covers:
- Permissions across roles (unauthenticated/guest/user/child) on pages.
- CRUD for categories and pages; tags exposed as a list.
- Visibility: a user's private page is hidden from another user and from children.
- Search: permission-filtered FTS over title/body/tags (SQLite icontains fallback).
- Hub widgets: wiki_favourites / wiki_emergency / wiki_recent assemble filtered content.
- Seed migration: default categories exist.
"""
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.home_wiki.models import WikiCategory, WikiPage
from apps.home_wiki.services import create_category, create_page


def _make_user(username, role=User.Role.ADMIN, is_child=False) -> User:
    user = User.objects.create_user(
        username=username, display_name=username.capitalize(), role=role, password="pass123!"
    )
    user.set_pin("1234")
    if is_child:
        user.is_child_account = True
    user.save()
    return user


def _login(client, username, pin="1234"):
    client.post(
        reverse("auth-pin-login"),
        {"username": username, "pin": pin},
        content_type="application/json",
    )


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

class WikiPermissionTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        self.user = _make_user("user", User.Role.USER)
        self.guest = _make_user("guest", User.Role.GUEST)
        self.child = _make_user("child", User.Role.USER, is_child=True)
        self.page_url = reverse("wiki-page-list")

    def test_unauthenticated_rejected(self):
        self.assertIn(self.client.get(self.page_url).status_code, [401, 403])

    def test_guest_can_view(self):
        _login(self.client, "guest")
        self.assertEqual(self.client.get(self.page_url).status_code, 200)

    def test_guest_cannot_create(self):
        _login(self.client, "guest")
        resp = self.client.post(self.page_url, {"title": "WiFi"}, content_type="application/json")
        self.assertIn(resp.status_code, [401, 403])

    def test_user_can_create(self):
        _login(self.client, "user")
        resp = self.client.post(self.page_url, {"title": "Bin night"}, content_type="application/json")
        self.assertEqual(resp.status_code, 201)

    def test_child_cannot_create(self):
        _login(self.client, "child")
        resp = self.client.post(self.page_url, {"title": "Rules"}, content_type="application/json")
        self.assertIn(resp.status_code, [401, 403])

    def test_user_cannot_delete(self):
        _login(self.client, "user")
        page = create_page(self.admin, title="Router reset")
        resp = self.client.delete(reverse("wiki-page-detail", args=[page.id]))
        self.assertIn(resp.status_code, [401, 403])

    def test_admin_can_delete(self):
        _login(self.client, "admin")
        page = create_page(self.admin, title="Router reset")
        resp = self.client.delete(reverse("wiki-page-detail", args=[page.id]))
        self.assertEqual(resp.status_code, 204)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

class WikiCrudTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        _login(self.client, "admin")

    def test_category_crud(self):
        resp = self.client.post(
            reverse("wiki-category-list"),
            {"name": "Garage", "colour": "#123456"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        cid = resp.json()["id"]
        resp = self.client.patch(
            reverse("wiki-category-detail", args=[cid]),
            {"is_hidden": True}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["is_hidden"])

    def test_page_create_with_category_and_tags(self):
        cat = create_category(self.admin, name="Internet")
        resp = self.client.post(
            reverse("wiki-page-list"),
            {"title": "WiFi", "body": "SSID + password", "category_id": cat.id,
             "tags": "wifi, internet, password", "is_favourite": True, "is_kiosk_safe": True},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["category_id"], cat.id)
        self.assertEqual(data["category_name"], "Internet")
        self.assertEqual(data["tag_list"], ["wifi", "internet", "password"])
        self.assertTrue(data["is_favourite"])

    def test_favourites_filter(self):
        create_page(self.admin, title="Pinned", is_favourite=True)
        create_page(self.admin, title="Normal")
        resp = self.client.get(reverse("wiki-page-list"), {"favourites": "1"})
        titles = [p["title"] for p in resp.json()]
        self.assertEqual(titles, ["Pinned"])

    def test_emergency_filter(self):
        create_page(self.admin, title="Emergency contacts", is_emergency=True)
        create_page(self.admin, title="Cleaning notes")
        resp = self.client.get(reverse("wiki-page-list"), {"emergency": "1"})
        titles = [p["title"] for p in resp.json()]
        self.assertEqual(titles, ["Emergency contacts"])


# ---------------------------------------------------------------------------
# Visibility (D10)
# ---------------------------------------------------------------------------

class WikiVisibilityTests(TestCase):
    def setUp(self):
        self.owner = _make_user("owner", User.Role.USER)
        self.other = _make_user("other", User.Role.USER)
        self.child = _make_user("child", User.Role.USER, is_child=True)
        self.private = create_page(self.owner, title="Owner secret", visibility="private")

    def test_owner_sees_own_private_page(self):
        from apps.home_wiki.selectors import list_pages
        self.assertIn("Owner secret", [p.title for p in list_pages(self.owner)])

    def test_other_user_cannot_see_private_page(self):
        from apps.home_wiki.selectors import list_pages
        self.assertNotIn("Owner secret", [p.title for p in list_pages(self.other)])

    def test_child_cannot_see_private_page(self):
        from apps.home_wiki.selectors import list_pages
        self.assertNotIn("Owner secret", [p.title for p in list_pages(self.child)])

    def test_child_cannot_see_sensitive_page(self):
        from apps.home_wiki.selectors import list_pages
        create_page(self.owner, title="Adult info", visibility="household", sensitivity="sensitive")
        self.assertNotIn("Adult info", [p.title for p in list_pages(self.child)])


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class WikiSearchTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        _login(self.client, "admin")

    def test_search_matches_title_body_tags(self):
        create_page(self.admin, title="Router reset", body="Hold the button 10s", tags="internet")
        create_page(self.admin, title="Bin night", body="Green bin Tuesday", tags="bins")
        resp = self.client.get(reverse("wiki-search"), {"q": "router"})
        self.assertEqual([p["title"] for p in resp.json()["pages"]], ["Router reset"])
        resp = self.client.get(reverse("wiki-search"), {"q": "internet"})
        self.assertEqual([p["title"] for p in resp.json()["pages"]], ["Router reset"])

    def test_empty_query_returns_empty(self):
        resp = self.client.get(reverse("wiki-search"), {"q": ""})
        self.assertEqual(resp.json(), {"pages": []})


# ---------------------------------------------------------------------------
# Hub widgets (Node Spec 8)
# ---------------------------------------------------------------------------

class WikiHubWidgetTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)

    def test_favourites_widget(self):
        from apps.hub.services import _wiki_widget_content
        create_page(self.admin, title="WiFi", is_favourite=True)
        create_page(self.admin, title="Nope")
        content = _wiki_widget_content("wiki_favourites", self.admin)
        self.assertEqual([p["title"] for p in content], ["WiFi"])

    def test_emergency_widget(self):
        from apps.hub.services import _wiki_widget_content
        create_page(self.admin, title="Emergency", is_emergency=True)
        content = _wiki_widget_content("wiki_emergency", self.admin)
        self.assertEqual([p["title"] for p in content], ["Emergency"])


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

class WikiSeedTests(TestCase):
    def test_default_categories_seeded(self):
        names = set(WikiCategory.objects.values_list("name", flat=True))
        self.assertIn("Emergency", names)
        self.assertIn("Utilities", names)
