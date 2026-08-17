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
        from apps.scheduling.sources.fetching import resolve_public_address

        for host in ("homestack-backend", "homestack-postgres", "nginx-proxy-manager"):
            with patch("apps.scheduling.sources.fetching.socket.getaddrinfo") as resolver:
                resolver.return_value = [(2, 1, 6, "", ("172.18.0.3", 80))]
                with self.assertRaises(CalendarFetchError, msg=host):
                    resolve_public_address(host, 80)

    def test_a_host_resolving_to_any_private_address_is_refused(self):
        """One public answer does not make a mixed-answer name safe."""
        from apps.scheduling.sources.fetching import resolve_public_address

        with patch("apps.scheduling.sources.fetching.socket.getaddrinfo") as resolver:
            resolver.return_value = [
                (2, 1, 6, "", ("93.184.216.34", 443)),
                (2, 1, 6, "", ("127.0.0.1", 443)),
            ]
            with self.assertRaises(CalendarFetchError):
                resolve_public_address("sneaky.example.com", 443)

    def test_resolution_returns_the_address_the_socket_must_use(self):
        from apps.scheduling.sources.fetching import resolve_public_address

        with patch("apps.scheduling.sources.fetching.socket.getaddrinfo") as resolver:
            resolver.return_value = [(2, 1, 6, "", ("93.184.216.34", 443))]
            self.assertEqual(resolve_public_address("example.com", 443), "93.184.216.34")

    def test_connection_is_pinned_to_the_validated_address_not_re_resolved(self):
        """The DNS-rebinding regression test.

        DNS answers with a public address while the URL is being validated, then with a private
        one on every later lookup. If anything resolved the *hostname* again to open the socket,
        the connection would land on 127.0.0.1. The connection must instead be constructed
        against the address that was validated.
        """
        from apps.scheduling.sources import fetching

        answers = [
            [(2, 1, 6, "", ("93.184.216.34", 443))],   # first lookup: public, passes validation
            [(2, 1, 6, "", ("127.0.0.1", 443))],       # every later lookup: rebound to loopback
        ]

        def flipping_resolver(*args, **kwargs):
            return answers.pop(0) if len(answers) > 1 else answers[0]

        with patch.object(fetching.socket, "getaddrinfo", side_effect=flipping_resolver), \
             patch.object(fetching, "_PinnedHTTPSConnection", _RecordingConnection):
            _RecordingConnection.reset(body=_CALENDAR_BODY)
            text = fetching.fetch_calendar("https://rebind.example.com/feed.ics")

        self.assertIn("BEGIN:VCALENDAR", text)
        # The one thing that matters: the connection was built for the validated address, and
        # never for the address a second lookup would have handed back.
        self.assertEqual(_RecordingConnection.pinned, ["93.184.216.34"])
        self.assertNotIn("127.0.0.1", _RecordingConnection.pinned)
        # Resolution happened exactly once for this hop.
        self.assertEqual(len(answers), 1)

    def test_connect_opens_the_socket_on_the_pinned_address_only(self):
        """connect() itself must use the pinned address, never self.host."""
        from apps.scheduling.sources import fetching

        connection = fetching._PinnedHTTPSConnection(
            "example.com", 443, pinned_ip="93.184.216.34", timeout=5,
        )
        opened = []

        class _Ctx:
            def wrap_socket(self, sock, server_hostname=None):
                opened.append(("sni", server_hostname))
                return sock

        connection._context = _Ctx()

        def fake_create_connection(address, timeout=None):
            opened.append(("socket", address))
            return object()

        with patch.object(fetching.socket, "create_connection", side_effect=fake_create_connection):
            connection.connect()

        self.assertIn(("socket", ("93.184.216.34", 443)), opened)
        # ...while TLS still verifies the hostname, so pinning costs nothing in TLS security.
        self.assertIn(("sni", "example.com"), opened)
        # And http.client derives Host: from .host, which is still the hostname.
        self.assertEqual(connection.host, "example.com")

    def test_redirect_to_a_private_address_is_refused(self):
        """Validating only the URL the user typed is not enough.

        `_open` runs for real here, so the redirect target is genuinely resolved and validated.
        """
        from apps.scheduling.sources import fetching

        with patch.object(fetching, "_PinnedHTTPSConnection", _RecordingConnection), \
             patch.object(fetching, "_PinnedHTTPConnection", _RecordingConnection), \
             patch.object(fetching.socket, "getaddrinfo",
                          return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]):
            _RecordingConnection.reset(status=302, location="http://169.254.169.254/latest/meta-data/")
            with self.assertRaises(CalendarFetchError) as caught:
                fetching.fetch_calendar("https://example.com/feed.ics")
        self.assertIn("local network", str(caught.exception))

    def test_redirect_to_an_internal_container_name_is_refused(self):
        from apps.scheduling.sources import fetching

        hops = {"n": 0}

        def resolver(host, port, **kwargs):
            hops["n"] += 1
            # The first hop is a genuine public host; the redirect target is internal.
            if hops["n"] == 1:
                return [(2, 1, 6, "", ("93.184.216.34", 443))]
            return [(2, 1, 6, "", ("172.18.0.3", 80))]

        with patch.object(fetching, "_PinnedHTTPSConnection", _RecordingConnection), \
             patch.object(fetching, "_PinnedHTTPConnection", _RecordingConnection), \
             patch.object(fetching.socket, "getaddrinfo", side_effect=resolver):
            _RecordingConnection.reset(status=302, location="http://homestack-postgres/feed.ics")
            with self.assertRaises(CalendarFetchError) as caught:
                fetching.fetch_calendar("https://example.com/feed.ics")
        self.assertIn("local network", str(caught.exception))

    def test_oversized_response_is_refused(self):
        from apps.scheduling.sources import fetching

        class _Response:
            status = 200

            def getheader(self, name, default=None):
                return default

            def read(self, size):
                return b"x" * size

        with patch.object(fetching, "_open", return_value=(_Conn(), _Response())):
            with self.assertRaises(CalendarFetchError) as caught:
                fetching.fetch_calendar("https://example.com/feed.ics", max_bytes=1024)
        self.assertIn("too large", str(caught.exception))

    def test_declared_oversized_content_length_is_refused_before_reading(self):
        from apps.scheduling.sources import fetching

        class _Response:
            status = 200

            def getheader(self, name, default=None):
                return "99999999" if name == "Content-Length" else default

            def read(self, size):  # pragma: no cover - must not be reached
                raise AssertionError("body should not be read when the length is already too big")

        with patch.object(fetching, "_open", return_value=(_Conn(), _Response())):
            with self.assertRaises(CalendarFetchError):
                fetching.fetch_calendar("https://example.com/feed.ics", max_bytes=1024)

    def test_non_calendar_response_is_refused(self):
        from apps.scheduling.sources import fetching

        class _Response:
            status = 200

            def getheader(self, name, default=None):
                return default

            def read(self, size):
                return b"<html><script>alert(1)</script></html>"

        with patch.object(fetching, "_open", return_value=(_Conn(), _Response())):
            with self.assertRaises(CalendarFetchError):
                fetching.fetch_calendar("https://example.com/not-a-calendar")

    def test_too_many_redirects_is_refused(self):
        from apps.scheduling.sources import fetching

        class _Redirect:
            status = 302

            def getheader(self, name, default=None):
                return "https://example.com/again.ics" if name == "Location" else default

        with patch.object(fetching, "_open", return_value=(_Conn(), _Redirect())):
            with self.assertRaises(CalendarFetchError) as caught:
                fetching.fetch_calendar("https://example.com/feed.ics")
        self.assertIn("redirected too many times", str(caught.exception))


_CALENDAR_BODY = (
    b"BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:a@x\r\nDTSTART:20260821T195000Z\r\n"
    b"SUMMARY:Match\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
)


class _Conn:
    """Stand-in for a pinned connection in tests that patch `_open` directly."""

    def close(self):
        pass


class _RecordingConnection:
    """A pinned-connection stand-in that records the address it was constructed for.

    Substituted for the real connection classes so `_open` — including resolution and
    validation — runs for real, while nothing touches the network.
    """

    pinned: list[str] = []
    _status = 200
    _location = None
    _body = _CALENDAR_BODY

    @classmethod
    def reset(cls, *, status=200, location=None, body=_CALENDAR_BODY):
        cls.pinned = []
        cls._status, cls._location, cls._body = status, location, body

    def __init__(self, host, port, *, pinned_ip, timeout, context=None):
        self.host, self.port, self._pinned_ip = host, port, pinned_ip
        type(self).pinned.append(pinned_ip)

    def request(self, method, target, headers=None):
        self.headers = headers or {}

    def getresponse(self):
        outer = type(self)

        class _Response:
            status = outer._status

            def getheader(self, name, default=None):
                if name == "Location":
                    return outer._location
                return default

            def read(self, size):
                return outer._body

        return _Response()

    def close(self):
        pass


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
    """Dates come from the jurisdiction that declares them, never from a derived rule."""

    def _names(self, year, **kwargs):
        return [h.name for h in au_holidays.holidays_for(year=year, state="QLD", **kwargs)]

    def test_queensland_2026_matches_the_published_list(self):
        expected = {
            (date(2026, 1, 1), "New Year's Day"),
            (date(2026, 1, 26), "Australia Day"),
            (date(2026, 4, 3), "Good Friday"),
            (date(2026, 4, 4), "The day after Good Friday"),
            (date(2026, 4, 5), "Easter Sunday"),
            (date(2026, 4, 6), "Easter Monday"),
            (date(2026, 4, 25), "Anzac Day"),
            (date(2026, 5, 4), "Labour Day"),
            (date(2026, 10, 5), "King's Birthday"),
            (date(2026, 12, 24), "Christmas Eve (from 6pm)"),
            (date(2026, 12, 25), "Christmas Day"),
            (date(2026, 12, 26), "Boxing Day"),
            (date(2026, 12, 28), "Boxing Day (additional)"),
        }
        actual = {(h.day, h.name) for h in au_holidays.holidays_for(year=2026, state="QLD")}
        self.assertEqual(actual, expected)

    def test_queensland_2027_matches_the_published_list(self):
        actual = {(h.day, h.name) for h in au_holidays.holidays_for(year=2027, state="QLD")}
        self.assertIn((date(2027, 3, 26), "Good Friday"), actual)
        self.assertIn((date(2027, 3, 28), "Easter Sunday"), actual)
        self.assertIn((date(2027, 5, 3), "Labour Day"), actual)
        self.assertIn((date(2027, 10, 4), "King's Birthday"), actual)

    def test_anzac_day_substitution_follows_the_jurisdiction_not_a_weekend_rule(self):
        """25 April 2026 is a Saturday (no Queensland substitute); 2027 is a Sunday (one is)."""
        days_2026 = {h.day for h in au_holidays.holidays_for(year=2026, state="QLD")
                     if h.name == "Anzac Day"}
        self.assertEqual(days_2026, {date(2026, 4, 25)})

        days_2027 = {h.day for h in au_holidays.holidays_for(year=2027, state="QLD")
                     if h.name == "Anzac Day"}
        self.assertEqual(days_2027, {date(2027, 4, 26)})

    def test_christmas_and_boxing_day_substitutes_are_published_not_computed(self):
        names_2026 = self._names(2026)
        self.assertIn("Boxing Day (additional)", names_2026)
        self.assertNotIn("Christmas Day (additional)", names_2026)

        names_2027 = self._names(2027)
        self.assertIn("Christmas Day (additional)", names_2027)
        self.assertIn("Boxing Day (additional)", names_2027)

    def test_christmas_eve_is_a_part_day_holiday(self):
        eve = next(h for h in au_holidays.holidays_for(year=2026, state="QLD")
                   if h.day == date(2026, 12, 24))
        self.assertTrue(eve.is_part_day)
        self.assertEqual(eve.starts_at.hour, 18)

    def test_official_naming_is_used(self):
        """Queensland gazettes "the day after Good Friday", not "Easter Saturday"."""
        names = self._names(2026)
        self.assertIn("The day after Good Friday", names)
        self.assertNotIn("Easter Saturday", names)

    def test_only_verified_jurisdictions_are_supported(self):
        self.assertEqual(au_holidays.SUPPORTED_REGIONS, ("QLD",))
        self.assertTrue(au_holidays.is_supported_region("qld"))
        self.assertFalse(au_holidays.is_supported_region("VIC"))
        for region in ("VIC", "NSW", "WA", "SA", "TAS", "NT", "ACT"):
            self.assertEqual(
                au_holidays.holidays_for(year=2026, state=region), [],
                f"{region} must not silently borrow another jurisdiction's holidays",
            )

    def test_unpublished_years_produce_nothing(self):
        self.assertEqual(au_holidays.holidays_for(year=2030, state="QLD"), [])

    def test_local_show_holiday_follows_the_configured_locality(self):
        brisbane = [h.name for h in au_holidays.holidays_for(
            year=2026, state="QLD", locality="brisbane")]
        townsville = [h.name for h in au_holidays.holidays_for(
            year=2026, state="QLD", locality="townsville")]
        self.assertIn("Royal Queensland Show (Ekka)", brisbane)
        self.assertNotIn("Royal Queensland Show (Ekka)", townsville)
        self.assertIn("Townsville Annual Show", townsville)

    def test_show_holiday_dates_match_the_published_show_list(self):
        expected = {
            "brisbane": date(2026, 8, 12),
            "gold_coast": date(2026, 8, 28),
            "toowoomba": date(2026, 3, 27),
            "cairns": date(2026, 7, 17),
            "townsville": date(2026, 7, 6),
        }
        for locality, day in expected.items():
            shows = [h for h in au_holidays.holidays_for(
                year=2026, state="QLD", locality=locality) if h.scope == au_holidays.LOCAL]
            self.assertEqual([h.day for h in shows], [day], locality)

    def test_a_locality_from_another_state_is_ignored(self):
        names = [h.name for h in au_holidays.holidays_for(
            year=2026, state="VIC", locality="brisbane")]
        self.assertNotIn("Royal Queensland Show (Ekka)", names)

    def test_levels_can_be_switched_off_independently(self):
        without_local = au_holidays.holidays_for(
            year=2026, state="QLD", locality="brisbane", include_local=False,
        )
        self.assertNotIn("Royal Queensland Show (Ekka)", [h.name for h in without_local])
        self.assertIn("Australia Day", [h.name for h in without_local])

        without_state = au_holidays.holidays_for(
            year=2026, state="QLD", locality="brisbane", include_regional=False,
        )
        self.assertEqual([h.name for h in without_state], ["Royal Queensland Show (Ekka)"])


class SchoolCalendarTests(TestCase):
    def setUp(self):
        self.admin = _make_user()
        self.household = get_active_household()

    def _source(self, system="qld_state", **settings):
        base = {"system": system, "show_terms": True, "show_holidays": True}
        base.update(settings)
        return CalendarSource.objects.create(
            household=self.household, created_by=self.admin, updated_by=self.admin,
            name=au_school.system_label(system), kind="school", provider="au_school_terms",
            settings_json=base,
        )

    def test_queensland_2026_matches_the_published_term_dates(self):
        self.assertEqual(
            [(t.number, t.start, t.end) for t in au_school.terms_for("qld_state", 2026)],
            [
                (1, date(2026, 1, 27), date(2026, 4, 2)),
                (2, date(2026, 4, 20), date(2026, 6, 26)),
                (3, date(2026, 7, 13), date(2026, 9, 18)),
                (4, date(2026, 10, 6), date(2026, 12, 11)),
            ],
        )

    def test_queensland_2027_is_published(self):
        """2027 is already official, so the calendar must not stop at December 2026."""
        self.assertEqual(
            [(t.number, t.start, t.end) for t in au_school.terms_for("qld_state", 2027)],
            [
                (1, date(2027, 1, 27), date(2027, 3, 25)),
                (2, date(2027, 4, 12), date(2027, 6, 25)),
                (3, date(2027, 7, 12), date(2027, 9, 17)),
                (4, date(2027, 10, 5), date(2027, 12, 10)),
            ],
        )

    def test_nsw_divisions_have_different_student_start_dates(self):
        """Eastern students return 2 Feb 2026, Western 9 Feb — a real, published difference."""
        eastern = au_school.terms_for("nsw_state_eastern", 2026)[0]
        western = au_school.terms_for("nsw_state_western", 2026)[0]
        self.assertEqual(eastern.start, date(2026, 2, 2))
        self.assertEqual(western.start, date(2026, 2, 9))
        self.assertEqual(eastern.end, western.end)

    def test_nsw_term_one_does_not_use_the_school_development_day(self):
        """Development days run 27-30 January 2026; students are not at school then."""
        eastern = au_school.terms_for("nsw_state_eastern", 2026)[0]
        self.assertNotEqual(eastern.start, date(2026, 1, 27))
        self.assertGreater(eastern.start, date(2026, 1, 30))

    def test_both_nsw_divisions_are_offered_as_separate_systems(self):
        self.assertIn("nsw_state_eastern", au_school.SCHOOL_SYSTEMS)
        self.assertIn("nsw_state_western", au_school.SCHOOL_SYSTEMS)
        self.assertIn("Eastern", au_school.system_label("nsw_state_eastern"))
        self.assertIn("Western", au_school.system_label("nsw_state_western"))

    def test_unverified_systems_are_not_offered(self):
        self.assertNotIn("vic_state", au_school.SCHOOL_SYSTEMS)
        self.assertEqual(au_school.terms_for("vic_state", 2026), [])

    def test_terms_are_ranges_not_one_event_per_day(self):
        entries = au_school.build_events(self._source(), household=self.household, years=(2026,))
        terms = [row for row in entries if row["summary"].startswith("Term")]
        self.assertEqual(len(terms), 4)
        self.assertTrue(all(row["is_range"] for row in terms))

    def test_holidays_fill_the_gaps_between_terms(self):
        entries = au_school.build_events(self._source(), household=self.household, years=(2026,))
        breaks = [row for row in entries if row["summary"] == "School holidays"]
        september = next(row for row in breaks if row["start_date"] == date(2026, 9, 19))
        self.assertEqual(september["end_date"], date(2026, 10, 5))

    def test_the_summer_break_is_only_produced_when_the_next_year_is_published(self):
        entries = au_school.build_events(self._source(), household=self.household, years=(2027,))
        breaks = [row for row in entries if row["summary"] == "School holidays"]
        self.assertTrue(all(row["end_date"].year == 2027 for row in breaks))

    def test_terms_and_holidays_toggle_independently(self):
        no_terms = au_school.build_events(
            self._source(show_terms=False), household=self.household, years=(2026,))
        self.assertFalse([r for r in no_terms if r["summary"].startswith("Term")])
        self.assertTrue([r for r in no_terms if r["summary"] == "School holidays"])

        no_holidays = au_school.build_events(
            self._source(show_holidays=False), household=self.household, years=(2026,))
        self.assertFalse([r for r in no_holidays if r["summary"] == "School holidays"])

    def test_student_free_days_produce_nothing_until_data_exists(self):
        """The toggle must not imply data we do not have."""
        entries = au_school.build_events(
            self._source(show_student_free=True), household=self.household, years=(2026,))
        self.assertFalse([r for r in entries if r["summary"] == "Student-free day"])

    def test_resync_does_not_duplicate_terms(self):
        source = self._source()
        for _ in range(3):
            entries = au_school.build_events(source, household=self.household, years=(2026,))
            apply_events(source, entries, household_zone=BRISBANE)
        self.assertEqual(
            CalendarEvent.objects.filter(calendar_source=source, title="Term 3").count(), 1,
        )



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


class SourceManagedEventWriteTests(TestCase):
    """A source-managed entry must not be editable through the ordinary events API.

    `is_synced` alone did not cover these: a CalendarSource entry leaves `source_record_*`
    empty, so every holiday, school range, subscribed fixture and imported event passed the
    guard and could be PATCHed or DELETEd — with the next sync quietly reinstating it.
    """

    def setUp(self):
        self.admin = _make_user()
        self.household = get_active_household()
        self.client.force_login(self.admin)

    def _source(self, kind="subscription", provider="ics", **extra):
        return CalendarSource.objects.create(
            household=self.household, created_by=self.admin, updated_by=self.admin,
            name=f"{kind} source", kind=kind, provider=provider, **extra,
        )

    def _event_for(self, source):
        future = (timezone.now() + timedelta(days=10)).strftime("%Y%m%dT%H%M%SZ")
        apply_events(
            source,
            normalise_events(_ics(_vevent("x@x", future, summary="Managed entry")), BRISBANE),
            household_zone=BRISBANE,
        )
        return CalendarEvent.objects.get(calendar_source=source)

    def test_every_source_kind_refuses_patch_and_delete(self):
        for kind, provider in (
            ("subscription", "ics"),
            ("import", "ics"),
            ("holidays", "au_holidays"),
            ("school", "au_school_terms"),
        ):
            source = self._source(kind=kind, provider=provider)
            event = self._event_for(source)
            url = reverse("calendar-event-detail", args=[event.id])

            patched = self.client.patch(
                url, {"title": "Hijacked"}, content_type="application/json",
            )
            self.assertEqual(patched.status_code, 400, f"{kind}: PATCH should be refused")
            deleted = self.client.delete(url)
            self.assertEqual(deleted.status_code, 400, f"{kind}: DELETE should be refused")

            event.refresh_from_db()
            self.assertEqual(event.title, "Managed entry")
            self.assertIsNone(event.deleted_at)

    def test_the_refusal_says_where_to_change_it(self):
        source = self._source()
        event = self._event_for(source)
        response = self.client.patch(
            reverse("calendar-event-detail", args=[event.id]),
            {"title": "Hijacked"}, content_type="application/json",
        )
        self.assertIn("calendar source", response.json()["detail"].lower())

    def test_the_service_layer_refuses_too_not_only_the_view(self):
        from apps.scheduling.services import delete_event, update_event

        source = self._source()
        event = self._event_for(source)
        with self.assertRaises(ValueError):
            update_event(self.admin, event, title="Hijacked")
        with self.assertRaises(ValueError):
            delete_event(self.admin, event)

    def test_hand_made_events_are_still_editable(self):
        event = create_event(self.admin, title="Family dinner", start_at=timezone.now() + timedelta(days=1))
        url = reverse("calendar-event-detail", args=[event.id])
        self.assertEqual(
            self.client.patch(url, {"title": "Dinner"}, content_type="application/json").status_code,
            200,
        )
        self.assertEqual(self.client.delete(url).status_code, 204)


class SubscriptionUrlSecrecyTests(TestCase):
    """A tokenised ICS link is a bearer credential and must never come back over the API."""

    SECRET_URL = "https://feeds.example.com/team/fixtures.ics?key=SUPERSECRETTOKEN123"

    def setUp(self):
        self.admin = _make_user()
        self.client.force_login(self.admin)
        self.source = CalendarSource.objects.create(
            household=get_active_household(), created_by=self.admin, updated_by=self.admin,
            name="Broncos", kind="subscription", provider="ics", url=self.SECRET_URL,
        )

    def test_list_response_contains_no_part_of_the_url(self):
        body = self.client.get(reverse("calendar-source-list")).content.decode()
        self.assertNotIn("SUPERSECRETTOKEN123", body)
        self.assertNotIn("key=", body)
        self.assertNotIn("/team/fixtures.ics", body)
        self.assertNotIn(self.SECRET_URL, body)

    def test_only_safe_metadata_is_exposed(self):
        row = self.client.get(reverse("calendar-source-list")).json()["sources"][0]
        self.assertNotIn("url", row)
        self.assertTrue(row["has_url"])
        self.assertEqual(row["url_display"], "feeds.example.com")

    def test_update_response_also_withholds_the_url(self):
        body = self.client.patch(
            reverse("calendar-source-detail", args=[self.source.id]),
            {"name": "Broncos fixtures"}, content_type="application/json",
        ).content.decode()
        self.assertNotIn("SUPERSECRETTOKEN123", body)

    def test_a_manager_can_replace_the_url_without_being_given_the_old_one(self):
        replacement = "https://feeds.example.com/team/new.ics?key=NEWTOKEN"
        # Stub only the DNS step so the real validation path still runs.
        with patch("apps.scheduling.sources.fetching.resolve_public_address",
                   return_value="93.184.216.34"):
            response = self.client.patch(
                reverse("calendar-source-detail", args=[self.source.id]),
                {"url": replacement}, content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)
        self.source.refresh_from_db()
        self.assertEqual(self.source.url, replacement)
        self.assertNotIn("NEWTOKEN", response.content.decode())

    def test_sync_errors_do_not_echo_the_url(self):
        from apps.scheduling.sources.sync import sync_source

        # An unexpected library error that quotes the URL it was handed.
        with patch("apps.scheduling.sources.feeds.fetch_calendar",
                   side_effect=RuntimeError(f"failed opening {self.SECRET_URL}")):
            result = sync_source(self.source)
        self.source.refresh_from_db()
        self.assertNotIn("SUPERSECRETTOKEN123", self.source.sync_error)
        self.assertNotIn("SUPERSECRETTOKEN123", result["error"])
        self.assertNotIn("SUPERSECRETTOKEN123", self.client.get(reverse("calendar-source-list")).content.decode())


class DisabledSourceSearchTests(TestCase):
    """Disabling a source must hide its entries from search too, not just the calendar."""

    def setUp(self):
        self.admin = _make_user()
        self.source = CalendarSource.objects.create(
            household=get_active_household(), created_by=self.admin, updated_by=self.admin,
            name="Broncos", kind="subscription", provider="ics", url="https://example.com/f.ics",
        )
        future = (timezone.now() + timedelta(days=6)).strftime("%Y%m%dT%H%M%SZ")
        apply_events(
            self.source,
            normalise_events(_ics(_vevent("m@x", future, summary="Broncos vs Cowboys")), BRISBANE),
            household_zone=BRISBANE,
        )

    def _search(self, term="Broncos"):
        from apps.scheduling.selectors import search_events
        return [event.title for event in search_events(self.admin, term)]

    def test_enabled_source_is_searchable(self):
        self.assertIn("Broncos vs Cowboys", self._search())

    def test_disabled_source_is_not_searchable(self):
        self.source.is_enabled = False
        self.source.save()
        self.assertNotIn("Broncos vs Cowboys", self._search())

    def test_source_hidden_from_the_calendar_is_not_searchable(self):
        self.source.show_on_calendar = False
        self.source.save()
        self.assertNotIn("Broncos vs Cowboys", self._search())

    def test_hand_made_events_remain_searchable(self):
        create_event(self.admin, title="Broncos party", start_at=timezone.now() + timedelta(days=2))
        self.source.is_enabled = False
        self.source.save()
        self.assertIn("Broncos party", self._search())


class PartDayHolidayTests(TestCase):
    """A part-day holiday must be stored as a timed, timezone-aware entry."""

    def setUp(self):
        self.admin = _make_user()
        household = get_active_household()
        household.country, household.region = "AU", "QLD"
        household.timezone = "Australia/Brisbane"
        household.save()
        self.household = household
        self.source = CalendarSource.objects.create(
            household=household, created_by=self.admin, updated_by=self.admin,
            name="Queensland public holidays", kind="holidays", provider="au_holidays",
        )

    def test_christmas_eve_is_timed_not_all_day(self):
        sync_source(self.source, household=self.household)
        eve = CalendarEvent.objects.get(title="Christmas Eve (from 6pm)",
                                        start_at__year=2026)
        self.assertFalse(eve.is_all_day)
        self.assertEqual(eve.start_at.astimezone(BRISBANE).hour, 18)

    def test_stored_times_are_timezone_aware(self):
        """A naive datetime reaching the ORM is a real bug, not a warning to live with."""
        sync_source(self.source, household=self.household)
        for event in CalendarEvent.objects.filter(calendar_source=self.source):
            self.assertIsNotNone(event.start_at.tzinfo, event.title)
            if event.end_at:
                self.assertIsNotNone(event.end_at.tzinfo, event.title)

    def test_full_day_holidays_remain_all_day(self):
        sync_source(self.source, household=self.household)
        christmas = CalendarEvent.objects.get(title="Christmas Day", start_at__year=2026)
        self.assertTrue(christmas.is_all_day)
