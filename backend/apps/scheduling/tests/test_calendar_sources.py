"""Calendar Sources — SSRF boundary, ICS sync semantics, and jurisdiction correctness.

Every test uses fixture data or a patched fetcher. Nothing here touches the network: a suite
that depended on a live council or sports website would fail for reasons that have nothing to
do with HomeStack.
"""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.scheduling.models import CalendarEvent, CalendarSource
from apps.scheduling.services import create_calendar_source, create_event
from apps.scheduling.sources import au_holidays, au_school
from apps.scheduling.sources.feeds import normalise_events
from apps.scheduling.sources.fetching import CalendarFetchError, normalise_url
from apps.scheduling.sources.ics import IcsParseError, parse_calendar
from apps.scheduling.sources.sync import apply_events, sync_due_sources, sync_source

BRISBANE = ZoneInfo("Australia/Brisbane")


def _make_user(username="admin", role=User.Role.ADMIN) -> User:
    user = User.objects.create_user(
        username=username, display_name=username.capitalize(), role=role, password="pass123!",
    )
    user.set_pin("1234")
    user.save()
    return user


def _ics(*vevents: str) -> str:
    body = "\r\n".join(vevents)
    return f"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//test//EN\r\n{body}\r\nEND:VCALENDAR\r\n"


def _vevent(uid: str, start: str, end: str = "", summary: str = "Match",
            location: str = "", status: str = "", sequence: str = "") -> str:
    lines = [f"BEGIN:VEVENT", f"UID:{uid}", f"DTSTART:{start}", f"SUMMARY:{summary}"]
    if end:
        lines.append(f"DTEND:{end}")
    if location:
        lines.append(f"LOCATION:{location}")
    if status:
        lines.append(f"STATUS:{status}")
    if sequence:
        lines.append(f"SEQUENCE:{sequence}")
    lines.append("END:VEVENT")
    return "\r\n".join(lines)


# ---------------------------------------------------------------------------
# SSRF boundary
# ---------------------------------------------------------------------------

class CalendarFetchSsrfTests(TestCase):
    """The server fetches URLs the household supplies, beside Postgres on a LAN. Fail closed."""

    def test_webcal_is_normalised_to_https(self):
        self.assertEqual(
            normalise_url("webcal://example.com/feed.ics"), "https://example.com/feed.ics",
        )
        self.assertEqual(
            normalise_url("webcals://example.com/feed.ics"), "https://example.com/feed.ics",
        )

    def test_non_http_schemes_are_refused(self):
        for url in (
            "file:///etc/passwd",
            "ftp://example.com/feed.ics",
            "gopher://example.com/",
            "data:text/calendar;base64,QkVHSU4=",
        ):
            with self.assertRaises(CalendarFetchError, msg=url):
                normalise_url(url)

    def test_embedded_credentials_are_refused(self):
        with self.assertRaises(CalendarFetchError):
            normalise_url("https://user:secret@example.com/feed.ics")

    def test_literal_private_and_loopback_targets_are_refused(self):
        from apps.scheduling.sources.fetching import fetch_calendar

        for url in (
            "http://127.0.0.1/feed.ics",
            "http://localhost/feed.ics",       # resolves to loopback
            "http://[::1]/feed.ics",
            "http://10.0.0.5/feed.ics",
            "http://192.168.1.10/feed.ics",
            "http://172.16.4.4/feed.ics",
            "http://169.254.169.254/latest/meta-data/",  # cloud metadata
            "http://0.0.0.0/feed.ics",
            "http://[::ffff:127.0.0.1]/feed.ics",        # IPv4-mapped loopback
        ):
            with self.assertRaises(CalendarFetchError, msg=url):
                fetch_calendar(url)

    def test_internal_service_names_are_refused(self):
        """The container names an attacker would actually try on this deployment."""
        from apps.scheduling.sources.fetching import _check_host

        for host in ("homestack-backend", "homestack-postgres", "nginx-proxy-manager"):
            with patch("apps.scheduling.sources.fetching.socket.getaddrinfo") as resolver:
                resolver.return_value = [(2, 1, 6, "", ("172.18.0.3", 80))]
                with self.assertRaises(CalendarFetchError, msg=host):
                    _check_host(f"http://{host}/feed.ics")

    def test_a_host_resolving_to_any_private_address_is_refused(self):
        """One public answer does not make a mixed-answer name safe."""
        from apps.scheduling.sources.fetching import _check_host

        with patch("apps.scheduling.sources.fetching.socket.getaddrinfo") as resolver:
            resolver.return_value = [
                (2, 1, 6, "", ("93.184.216.34", 443)),
                (2, 1, 6, "", ("127.0.0.1", 443)),
            ]
            with self.assertRaises(CalendarFetchError):
                _check_host("https://sneaky.example.com/feed.ics")

    def test_redirect_to_a_private_address_is_refused(self):
        """Validating only the URL the user typed is not enough."""
        from apps.scheduling.sources import fetching

        calls = []

        def fake_check(url):
            calls.append(url)
            if "169.254.169.254" in url:
                raise CalendarFetchError("blocked")

        class _Redirect(Exception):
            pass

        with patch.object(fetching, "_check_host", side_effect=fake_check):
            import urllib.error
            error = urllib.error.HTTPError(
                "https://example.com/feed.ics", 302, "Found",
                {"Location": "http://169.254.169.254/latest/meta-data/"}, None,
            )
            with patch.object(fetching.urllib.request, "build_opener") as opener:
                opener.return_value.open.side_effect = error
                with self.assertRaises(CalendarFetchError):
                    fetching.fetch_calendar("https://example.com/feed.ics")
        self.assertIn("169.254.169.254", "".join(calls))

    def test_oversized_response_is_refused(self):
        from apps.scheduling.sources import fetching

        class _Response:
            headers = {}

            def read(self, size):
                return b"x" * size

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with patch.object(fetching, "_check_host", return_value=None), \
             patch.object(fetching.urllib.request, "build_opener") as opener:
            opener.return_value.open.return_value = _Response()
            with self.assertRaises(CalendarFetchError) as caught:
                fetching.fetch_calendar("https://example.com/feed.ics", max_bytes=1024)
        self.assertIn("too large", str(caught.exception))

    def test_non_calendar_response_is_refused(self):
        from apps.scheduling.sources import fetching

        class _Response:
            headers = {}

            def read(self, size):
                return b"<html><script>alert(1)</script></html>"

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with patch.object(fetching, "_check_host", return_value=None), \
             patch.object(fetching.urllib.request, "build_opener") as opener:
            opener.return_value.open.return_value = _Response()
            with self.assertRaises(CalendarFetchError):
                fetching.fetch_calendar("https://example.com/not-a-calendar")


# ---------------------------------------------------------------------------
# ICS parsing
# ---------------------------------------------------------------------------

class IcsParsingTests(TestCase):
    def test_parses_a_basic_event(self):
        events = parse_calendar(_ics(_vevent("a@x", "20260821T195000Z", summary="Broncos vs Cowboys")))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].uid, "a@x")
        self.assertEqual(events[0].summary, "Broncos vs Cowboys")

    def test_all_day_event_stays_all_day(self):
        events = parse_calendar(_ics(
            "BEGIN:VEVENT\r\nUID:d@x\r\nDTSTART;VALUE=DATE:20260126\r\n"
            "DTEND;VALUE=DATE:20260127\r\nSUMMARY:Australia Day\r\nEND:VEVENT",
        ))
        self.assertTrue(events[0].all_day)
        start, end, all_day = _resolve(events[0])
        self.assertTrue(all_day)
        # Exclusive DTEND must not stretch a one-day holiday across two days.
        self.assertEqual(start.date(), date(2026, 1, 26))
        self.assertEqual(end.date(), date(2026, 1, 26))

    def test_timezone_is_respected(self):
        events = parse_calendar(_ics(
            "BEGIN:VEVENT\r\nUID:t@x\r\nDTSTART;TZID=Australia/Brisbane:20260821T195000\r\n"
            "SUMMARY:Kick off\r\nEND:VEVENT",
        ))
        start, _, _ = _resolve(events[0])
        self.assertEqual(start.astimezone(BRISBANE).hour, 19)
        self.assertEqual(start.astimezone(ZoneInfo("UTC")).hour, 9)

    def test_folded_lines_and_escapes_are_decoded(self):
        raw = (
            "BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:f@x\r\nDTSTART:20260821T195000Z\r\n"
            "SUMMARY:Long title that is\r\n  folded across lines\r\n"
            "DESCRIPTION:Line one\\nLine two\\, with comma\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
        )
        event = parse_calendar(raw)[0]
        self.assertEqual(event.summary, "Long title that is folded across lines")
        self.assertIn("Line one\nLine two, with comma", event.description)

    def test_events_without_uid_or_start_are_skipped(self):
        with self.assertRaises(IcsParseError):
            parse_calendar(_ics("BEGIN:VEVENT\r\nSUMMARY:No identity\r\nEND:VEVENT"))

    def test_malformed_input_is_rejected_safely(self):
        for text in ("", "not a calendar at all", "BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n"):
            with self.assertRaises(IcsParseError):
                parse_calendar(text)

    def test_event_cap_is_enforced(self):
        many = _ics(*[_vevent(f"u{n}@x", "20260821T195000Z") for n in range(12)])
        with self.assertRaises(IcsParseError):
            parse_calendar(many, max_events=10)


def _resolve(event):
    from apps.scheduling.sources.ics import resolve_times
    return resolve_times(event, BRISBANE)


# ---------------------------------------------------------------------------
# Sync semantics
# ---------------------------------------------------------------------------

class IcsSyncTests(TestCase):
    def setUp(self):
        self.admin = _make_user()
        self.source = CalendarSource.objects.create(
            household=get_active_household(), created_by=self.admin, updated_by=self.admin,
            name="Broncos", kind="subscription", provider="ics",
            url="https://example.com/feed.ics", colour="#6F5AA8", category="subscription",
        )

    def _sync(self, text):
        entries = normalise_events(text, BRISBANE)
        return apply_events(self.source, entries, household_zone=BRISBANE)

    def test_one_uid_creates_one_event(self):
        self._sync(_ics(_vevent("m1@x", "20260821T195000Z", summary="Broncos vs Cowboys")))
        self.assertEqual(CalendarEvent.objects.filter(calendar_source=self.source).count(), 1)

    def test_repeated_sync_is_idempotent(self):
        text = _ics(_vevent("m1@x", "20260821T195000Z"))
        self._sync(text)
        self._sync(text)
        self._sync(text)
        self.assertEqual(CalendarEvent.objects.filter(calendar_source=self.source).count(), 1)

    def test_changed_start_updates_rather_than_duplicating(self):
        self._sync(_ics(_vevent("m1@x", "20260821T195000Z")))
        self._sync(_ics(_vevent("m1@x", "20260822T160000Z")))
        events = CalendarEvent.objects.filter(calendar_source=self.source)
        self.assertEqual(events.count(), 1)
        self.assertEqual(events.first().start_at.astimezone(ZoneInfo("UTC")).day, 22)

    def test_changed_title_and_venue_update(self):
        self._sync(_ics(_vevent("m1@x", "20260821T195000Z", summary="Old", location="Old Park")))
        self._sync(_ics(_vevent("m1@x", "20260821T195000Z", summary="New", location="Suncorp")))
        event = CalendarEvent.objects.get(calendar_source=self.source)
        self.assertEqual(event.title, "New")
        self.assertEqual(event.location, "Suncorp")

    def test_cancelled_event_is_removed(self):
        self._sync(_ics(_vevent("m1@x", "20260821T195000Z")))
        self._sync(_ics(_vevent("m1@x", "20260821T195000Z", status="CANCELLED")))
        self.assertEqual(CalendarEvent.objects.filter(calendar_source=self.source).count(), 0)

    def test_future_event_dropped_from_the_feed_is_removed(self):
        future = (timezone.now() + timedelta(days=30)).strftime("%Y%m%dT%H%M%SZ")
        self._sync(_ics(_vevent("keep@x", future), _vevent("drop@x", future)))
        self._sync(_ics(_vevent("keep@x", future)))
        remaining = list(CalendarEvent.objects.filter(calendar_source=self.source)
                         .values_list("external_uid", flat=True))
        self.assertEqual(remaining, ["keep@x"])

    def test_past_event_dropped_from_the_feed_is_kept(self):
        """A feed that only publishes the current season must not erase last season."""
        past = (timezone.now() - timedelta(days=60)).strftime("%Y%m%dT%H%M%SZ")
        future = (timezone.now() + timedelta(days=30)).strftime("%Y%m%dT%H%M%SZ")
        self._sync(_ics(_vevent("old@x", past), _vevent("new@x", future)))
        self._sync(_ics(_vevent("new@x", future)))
        remaining = set(CalendarEvent.objects.filter(calendar_source=self.source)
                        .values_list("external_uid", flat=True))
        self.assertEqual(remaining, {"old@x", "new@x"})

    def test_sync_does_not_touch_hand_made_events(self):
        create_event(self.admin, title="Family dinner", start_at=timezone.now() + timedelta(days=1))
        self._sync(_ics(_vevent("m1@x", "20260821T195000Z")))
        manual = CalendarEvent.objects.get(title="Family dinner")
        self.assertIsNone(manual.calendar_source_id)
        self.assertFalse(manual.is_source_managed)

    def test_deleting_a_source_removes_only_its_events(self):
        from apps.scheduling.services import delete_calendar_source

        create_event(self.admin, title="Family dinner", start_at=timezone.now() + timedelta(days=1))
        self._sync(_ics(_vevent("m1@x", "20260821T195000Z")))
        delete_calendar_source(self.admin, self.source)
        self.assertTrue(CalendarEvent.objects.filter(title="Family dinner").exists())
        self.assertEqual(CalendarEvent.objects.filter(external_uid="m1@x").count(), 0)

    def test_source_failure_is_recorded_not_raised(self):
        with patch("apps.scheduling.sources.feeds.fetch_calendar",
                   side_effect=CalendarFetchError("host unreachable")):
            result = sync_source(self.source)
        self.source.refresh_from_db()
        self.assertIn("error", result)
        self.assertEqual(self.source.sync_status, CalendarSource.Status.ERROR)
        self.assertIn("unreachable", self.source.sync_error)

    def test_one_failing_source_does_not_stop_the_others(self):
        good = CalendarSource.objects.create(
            household=get_active_household(), created_by=self.admin, updated_by=self.admin,
            name="Holidays", kind="holidays", provider="au_holidays",
            settings_json={"include_national": True},
        )
        with patch("apps.scheduling.sources.feeds.fetch_calendar",
                   side_effect=CalendarFetchError("down")):
            result = sync_due_sources()
        self.assertEqual(result["failed"], 1)
        self.assertGreaterEqual(result["synced"], 1)
        good.refresh_from_db()
        self.assertEqual(good.sync_status, CalendarSource.Status.OK)


# ---------------------------------------------------------------------------
# Jurisdiction correctness
# ---------------------------------------------------------------------------

class AustralianHolidayTests(TestCase):
    def test_national_holidays_apply_everywhere(self):
        names = [h.name for h in au_holidays.holidays_for(year=2026, state="QLD")]
        for expected in ("New Year's Day", "Australia Day", "Good Friday", "ANZAC Day",
                         "Christmas Day", "Boxing Day"):
            self.assertIn(expected, names)

    def test_state_holiday_does_not_leak_into_another_state(self):
        qld = [h.name for h in au_holidays.holidays_for(year=2026, state="QLD")]
        vic = [h.name for h in au_holidays.holidays_for(year=2026, state="VIC")]
        self.assertIn("Melbourne Cup Day", vic)
        self.assertNotIn("Melbourne Cup Day", qld)
        self.assertIn("Canberra Day", [h.name for h in au_holidays.holidays_for(year=2026, state="ACT")])
        self.assertNotIn("Canberra Day", qld)

    def test_queensland_labour_day_is_the_first_monday_in_may(self):
        labour = next(
            h for h in au_holidays.holidays_for(year=2026, state="QLD") if h.name == "Labour Day"
        )
        self.assertEqual(labour.day, date(2026, 5, 4))
        self.assertEqual(labour.day.weekday(), 0)

    def test_local_show_holiday_follows_the_configured_locality(self):
        brisbane = [h.name for h in au_holidays.holidays_for(
            year=2026, state="QLD", locality="brisbane")]
        cairns = [h.name for h in au_holidays.holidays_for(
            year=2026, state="QLD", locality="cairns")]
        self.assertIn("Brisbane Show Day (Ekka)", brisbane)
        self.assertNotIn("Brisbane Show Day (Ekka)", cairns)
        self.assertIn("Cairns Show Day", cairns)

    def test_a_locality_from_another_state_is_ignored(self):
        """A stale locality left behind after moving interstate must not inject its show day."""
        names = [h.name for h in au_holidays.holidays_for(
            year=2026, state="VIC", locality="brisbane")]
        self.assertNotIn("Brisbane Show Day (Ekka)", names)

    def test_levels_can_be_switched_off_independently(self):
        national_only = au_holidays.holidays_for(
            year=2026, state="QLD", locality="brisbane",
            include_regional=False, include_local=False,
        )
        names = [h.name for h in national_only]
        self.assertIn("Australia Day", names)
        self.assertNotIn("Labour Day", names)
        self.assertNotIn("Brisbane Show Day (Ekka)", names)

    def test_weekend_holidays_gain_an_observed_day(self):
        # 2027-01-01 is a Friday; 2026-01-01 is a Thursday. Use a year where it lands on a weekend.
        names = [(h.name, h.day) for h in au_holidays.holidays_for(year=2028, state="QLD")]
        new_year = [entry for entry in names if entry[0].startswith("New Year's Day")]
        self.assertTrue(any("observed" in name for name, _ in new_year))

    def test_easter_is_computed_correctly(self):
        self.assertEqual(au_holidays.easter_sunday(2026), date(2026, 4, 5))
        self.assertEqual(au_holidays.easter_sunday(2025), date(2025, 4, 20))


class SchoolCalendarTests(TestCase):
    def setUp(self):
        self.admin = _make_user()
        self.household = get_active_household()

    def _source(self, **settings):
        base = {"system": "qld_state", "show_terms": True, "show_holidays": True}
        base.update(settings)
        return CalendarSource.objects.create(
            household=self.household, created_by=self.admin, updated_by=self.admin,
            name="QLD State Schools", kind="school", provider="au_school_terms",
            settings_json=base,
        )

    def test_terms_are_ranges_not_one_event_per_day(self):
        entries = au_school.build_events(self._source(), household=self.household, years=(2026,))
        terms = [row for row in entries if row["summary"].startswith("Term")]
        self.assertEqual(len(terms), 4)
        self.assertTrue(all(row["is_range"] for row in terms))
        term3 = next(row for row in terms if row["summary"] == "Term 3")
        self.assertEqual(term3["start_date"], date(2026, 7, 13))
        self.assertEqual(term3["end_date"], date(2026, 9, 18))

    def test_holidays_fill_the_gaps_between_terms(self):
        entries = au_school.build_events(self._source(), household=self.household, years=(2026,))
        breaks = [row for row in entries if row["summary"] == "School holidays"]
        self.assertTrue(breaks)
        september = next(row for row in breaks if row["start_date"] == date(2026, 9, 19))
        self.assertEqual(september["end_date"], date(2026, 10, 5))

    def test_terms_and_holidays_toggle_independently(self):
        no_terms = au_school.build_events(
            self._source(show_terms=False), household=self.household, years=(2026,))
        self.assertFalse([r for r in no_terms if r["summary"].startswith("Term")])
        self.assertTrue([r for r in no_terms if r["summary"] == "School holidays"])

        no_holidays = au_school.build_events(
            self._source(show_holidays=False), household=self.household, years=(2026,))
        self.assertFalse([r for r in no_holidays if r["summary"] == "School holidays"])

    def test_resync_does_not_duplicate_terms(self):
        source = self._source()
        for _ in range(3):
            entries = au_school.build_events(source, household=self.household, years=(2026,))
            apply_events(source, entries, household_zone=BRISBANE)
        self.assertEqual(
            CalendarEvent.objects.filter(calendar_source=source, title="Term 3").count(), 1,
        )

    def test_different_systems_have_different_dates(self):
        qld = au_school.terms_for("qld_state", 2026)[0]
        nsw = au_school.terms_for("nsw_state", 2026)[0]
        # Systems differ at the boundaries, which is exactly why a school system is chosen
        # rather than inferred from the state alone.
        self.assertNotEqual(qld.start, nsw.start)


class HolidaySourceSyncTests(TestCase):
    """The holiday provider through the real sync path, keyed off household location."""

    def setUp(self):
        self.admin = _make_user()
        household = get_active_household()
        household.country = "AU"
        household.region = "QLD"
        household.locality = "brisbane"
        household.timezone = "Australia/Brisbane"
        household.save()
        self.household = household

    def _source(self, **settings):
        base = {"include_national": True, "include_regional": True, "include_local": True}
        base.update(settings)
        return CalendarSource.objects.create(
            household=self.household, created_by=self.admin, updated_by=self.admin,
            name="Australian public holidays", kind="holidays", provider="au_holidays",
            settings_json=base,
        )

    def test_sync_creates_holidays_for_the_configured_jurisdiction(self):
        source = self._source()
        sync_source(source, household=self.household)
        titles = set(CalendarEvent.objects.filter(calendar_source=source)
                     .values_list("title", flat=True))
        self.assertIn("Australia Day", titles)
        self.assertIn("Labour Day", titles)
        self.assertNotIn("Melbourne Cup Day", titles)

    def test_resync_does_not_duplicate(self):
        source = self._source()
        sync_source(source, household=self.household)
        first = CalendarEvent.objects.filter(calendar_source=source).count()
        sync_source(source, household=self.household)
        self.assertEqual(CalendarEvent.objects.filter(calendar_source=source).count(), first)

    def test_holidays_are_all_day_events_not_deadlines(self):
        source = self._source()
        sync_source(source, household=self.household)
        event = CalendarEvent.objects.filter(calendar_source=source).first()
        self.assertTrue(event.is_all_day)
        # Not a task: notification wording (0.38.0) must never call a holiday "due".
        self.assertNotEqual(event.event_kind, "task")


# ---------------------------------------------------------------------------
# API + permissions
# ---------------------------------------------------------------------------

class CalendarSourceApiTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin", User.Role.ADMIN)
        self.member = _make_user("member", User.Role.USER)
        self.url = reverse("calendar-source-list")

    def _login(self, user):
        self.client.force_login(user)

    def test_member_can_view_but_not_manage_sources(self):
        self._login(self.member)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        response = self.client.post(
            self.url,
            {"kind": "holidays", "provider": "au_holidays", "name": "Holidays"},
            content_type="application/json",
        )
        # Enforced on the server, not by hiding a button.
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_an_automatic_source(self):
        self._login(self.admin)
        response = self.client.post(
            self.url,
            {"kind": "holidays", "provider": "au_holidays", "name": "Australian public holidays"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.json())
        self.assertEqual(response.json()["kind"], "holidays")

    def test_unregistered_provider_is_rejected(self):
        self._login(self.admin)
        for payload in (
            {"kind": "holidays", "provider": "evil_provider"},
            {"kind": "whatever", "provider": "ics"},
        ):
            response = self.client.post(self.url, payload, content_type="application/json")
            self.assertEqual(response.status_code, 400, payload)

    def test_school_settings_are_validated(self):
        self._login(self.admin)
        bad = self.client.post(
            self.url,
            {"kind": "school", "provider": "au_school_terms", "settings_json": {"system": "hogwarts"}},
            content_type="application/json",
        )
        self.assertEqual(bad.status_code, 400)

    def test_subscription_url_is_validated_against_ssrf_on_create(self):
        self._login(self.admin)
        response = self.client.post(
            self.url,
            {"kind": "subscription", "provider": "ics", "name": "Bad", "url": "http://127.0.0.1/x.ics"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_disabled_source_is_skipped_by_scheduled_sync(self):
        source = CalendarSource.objects.create(
            household=get_active_household(), created_by=self.admin, updated_by=self.admin,
            name="Holidays", kind="holidays", provider="au_holidays", is_enabled=False,
        )
        result = sync_due_sources()
        source.refresh_from_db()
        self.assertEqual(source.sync_status, CalendarSource.Status.IDLE)
        self.assertEqual(result["synced"], 0)

    def test_import_source_reads_once_and_does_not_resync(self):
        self._login(self.admin)
        text = _ics(_vevent("i1@x", "20260821T195000Z", summary="Imported match"))
        response = self.client.post(
            self.url,
            {"kind": "import", "provider": "ics", "name": "Junior Rugby", "ics_text": text},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.json())
        source = CalendarSource.objects.get(pk=response.json()["id"])
        self.assertEqual(CalendarEvent.objects.filter(calendar_source=source).count(), 1)
        self.assertFalse(response.json()["can_sync"])
        self.assertEqual(sync_source(source), {"skipped": True})


class SourceVisibilityTests(TestCase):
    """A source's switches control where its entries appear — without deleting anything."""

    def setUp(self):
        self.admin = _make_user()
        self.household = get_active_household()
        self.source = CalendarSource.objects.create(
            household=self.household, created_by=self.admin, updated_by=self.admin,
            name="Broncos", kind="subscription", provider="ics",
            url="https://example.com/f.ics", category="subscription",
        )
        future = (timezone.now() + timedelta(days=5)).strftime("%Y%m%dT%H%M%SZ")
        apply_events(
            self.source,
            normalise_events(_ics(_vevent("m@x", future, summary="Broncos vs Cowboys")), BRISBANE),
            household_zone=BRISBANE,
        )

    def _titles(self, **kwargs):
        from apps.scheduling.selectors import list_events
        return [event.title for event in list_events(self.admin, **kwargs)]

    def test_enabled_source_appears_on_the_calendar(self):
        self.assertIn("Broncos vs Cowboys", self._titles())

    def test_disabled_source_is_hidden_but_not_deleted(self):
        self.source.is_enabled = False
        self.source.save()
        self.assertNotIn("Broncos vs Cowboys", self._titles())
        # Hidden, not destroyed — re-enabling brings it straight back with no re-sync.
        self.assertEqual(CalendarEvent.objects.filter(calendar_source=self.source).count(), 1)
        self.source.is_enabled = True
        self.source.save()
        self.assertIn("Broncos vs Cowboys", self._titles())

    def test_calendar_and_upcoming_toggles_are_independent(self):
        self.source.show_in_upcoming = False
        self.source.save()
        self.assertIn("Broncos vs Cowboys", self._titles())
        self.assertNotIn("Broncos vs Cowboys", self._titles(surface="upcoming"))

        self.source.show_in_upcoming = True
        self.source.show_on_calendar = False
        self.source.save()
        self.assertNotIn("Broncos vs Cowboys", self._titles())
        self.assertIn("Broncos vs Cowboys", self._titles(surface="upcoming"))

    def test_hiding_a_source_leaves_hand_made_events_alone(self):
        create_event(self.admin, title="Family dinner", start_at=timezone.now() + timedelta(days=2))
        self.source.is_enabled = False
        self.source.save()
        self.assertIn("Family dinner", self._titles())

    def test_source_filter_keeps_homestack_events_visible(self):
        create_event(self.admin, title="Family dinner", start_at=timezone.now() + timedelta(days=2))
        # "HomeStack only" is an empty source list, not an impossible id.
        titles = self._titles(source_ids=[])
        self.assertIn("Family dinner", titles)
        self.assertNotIn("Broncos vs Cowboys", titles)

        titles = self._titles(source_ids=[self.source.id])
        self.assertIn("Broncos vs Cowboys", titles)


class SourceNotificationTests(TestCase):
    """Subscribing to a season must not notify the household about every fixture."""

    def setUp(self):
        self.admin = _make_user()
        self.source = CalendarSource.objects.create(
            household=get_active_household(), created_by=self.admin, updated_by=self.admin,
            name="Broncos", kind="subscription", provider="ics",
            url="https://example.com/f.ics", notifications_enabled=False,
        )

    def _sweep_titles(self):
        from apps.notifications.tasks import _reminder_events
        return set(_reminder_events().values_list("title", flat=True))

    def test_source_events_are_silent_by_default(self):
        soon = (timezone.now() + timedelta(hours=24)).strftime("%Y%m%dT%H%M%SZ")
        apply_events(
            self.source,
            normalise_events(_ics(_vevent("m@x", soon, summary="Broncos vs Cowboys")), BRISBANE),
            household_zone=BRISBANE,
        )
        self.assertNotIn("Broncos vs Cowboys", self._sweep_titles())

    def test_source_events_notify_once_deliberately_enabled(self):
        self.source.notifications_enabled = True
        self.source.save()
        soon = (timezone.now() + timedelta(hours=24)).strftime("%Y%m%dT%H%M%SZ")
        apply_events(
            self.source,
            normalise_events(_ics(_vevent("m@x", soon, summary="Broncos vs Cowboys")), BRISBANE),
            household_zone=BRISBANE,
        )
        self.assertIn("Broncos vs Cowboys", self._sweep_titles())

    def test_a_fixture_is_worded_as_an_event_never_as_due(self):
        """Preserves the 0.38.0 wording rule: a fixture happens, it is not 'due'."""
        from apps.notifications import wording

        self.source.notifications_enabled = True
        self.source.save()
        soon = (timezone.now() + timedelta(hours=24)).strftime("%Y%m%dT%H%M%SZ")
        apply_events(
            self.source,
            normalise_events(_ics(_vevent("m@x", soon, summary="Broncos vs Cowboys")), BRISBANE),
            household_zone=BRISBANE,
        )
        event = CalendarEvent.objects.get(external_uid="m@x")
        self.assertEqual(wording.entry_kind(event), wording.EVENT)
        self.assertEqual(wording.tomorrow_title(event), "Tomorrow")
        self.assertNotIn("Due", wording.today_title(event, BRISBANE))
