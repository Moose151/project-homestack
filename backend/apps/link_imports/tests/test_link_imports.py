from datetime import datetime
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import Household
from apps.link_imports.extractors import extract_product
from apps.link_imports.fetch import FetchResult, LinkFetchError, fetch_public
from apps.link_imports.models import LinkWatch
from apps.link_imports.tasks import run_daily_price_watches
from apps.people.models import Person


class SafeFetchTests(TestCase):
    def test_loopback_is_rejected_before_connection(self):
        with self.assertRaises(LinkFetchError):
            fetch_public("http://127.0.0.1/admin")

    def test_private_dns_answer_is_rejected(self):
        with patch("apps.link_imports.fetch.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("192.168.1.8", 80))]):
            with self.assertRaises(LinkFetchError):
                fetch_public("http://shop.example/item")


class ProductExtractionTests(TestCase):
    def test_json_ld_product_is_preferred(self):
        html = b'''<html><head><script type="application/ld+json">{
          "@type":"Product","name":"Oak table","image":"/table.jpg",
          "offers":{"@type":"Offer","price":"149.00","priceCurrency":"AUD"}
        }</script><meta property="og:site_name" content="Example Shop"></head></html>'''
        with patch("apps.link_imports.extractors.fetch_public", return_value=FetchResult(
            url="https://shop.example/item", content=html, content_type="text/html",
            headers={"content-type": "text/html; charset=utf-8"},
        )):
            result = extract_product("https://shop.example/item")
        self.assertEqual(result["title"], "Oak table")
        self.assertEqual(result["price"], "149.00")
        self.assertEqual(result["image_url"], "https://shop.example/table.jpg")

    def test_visible_product_price_fallback_is_narrowly_recognised(self):
        html = b'''<html><head><meta property="og:title" content="Shelf"></head>
        <body><p data-locator="product-price">$52</p><b>$13 instalments</b></body></html>'''
        with patch("apps.link_imports.extractors.fetch_public", return_value=FetchResult(
            url="https://shop.example/shelf", content=html, content_type="text/html",
            headers={"content-type": "text/html; charset=utf-8"},
        )):
            result = extract_product("https://shop.example/shelf")
        self.assertEqual(result["price"], "52.00")

    def test_interruption_page_title_is_not_used_as_product_name(self):
        html = b'''<html><head><title>Pardon Our Interruption</title></head>
        <body><p data-locator="product-price">$2,977.00</p></body></html>'''
        with patch("apps.link_imports.extractors.fetch_public", return_value=FetchResult(
            url="https://www.harveynorman.com.au/tv.html", content=html, content_type="text/html",
            headers={"content-type": "text/html; charset=utf-8"},
        )):
            result = extract_product("https://www.harveynorman.com.au/tv.html")
        self.assertEqual(result["title"], "")
        self.assertEqual(result["price"], "2977.00")
        self.assertEqual(result["retailer"], "harveynorman.com.au")
        self.assertTrue(any("title was ignored" in warning for warning in result["warnings"]))
        self.assertTrue(any("image link manually" in warning for warning in result["warnings"]))


class PriceWatchScheduleTests(TestCase):
    def setUp(self):
        household = Household.objects.first() or Household.objects.create(name="Watch home", slug="watch-home", timezone="Australia/Brisbane")
        household.timezone = "Australia/Brisbane"
        household.save(update_fields=["timezone"])
        user = User.objects.create_user("watcher", "Watcher", password="pw", role=User.Role.USER)
        person = Person.objects.create(household=household, linked_user=user, display_name="Watcher", created_by=user, updated_by=user)
        self.watch = LinkWatch.objects.create(
            household=household, owner_person=person, source_node="atlas", source_record_type="AtlasListItem",
            source_record_id=1, url="https://shop.example/item", title="Item", currency="AUD",
            baseline_price=Decimal("100"), current_price=Decimal("100"), lowest_price=Decimal("100"),
            created_by=user, updated_by=user,
        )

    @patch("apps.link_imports.tasks.check_watch", return_value=True)
    def test_runs_once_after_nine_household_local_and_catches_up(self, check):
        before = datetime(2026, 8, 11, 8, 59, tzinfo=ZoneInfo("Australia/Brisbane"))
        self.assertEqual(run_daily_price_watches(now=before)["checked"], 0)
        after = datetime(2026, 8, 11, 10, 30, tzinfo=ZoneInfo("Australia/Brisbane"))
        self.assertEqual(run_daily_price_watches(now=after)["checked"], 1)
        self.assertEqual(run_daily_price_watches(now=after)["checked"], 0)
        check.assert_called_once()
