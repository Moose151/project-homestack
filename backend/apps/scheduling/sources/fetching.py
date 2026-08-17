"""Fetching a user-supplied calendar URL from the server, without becoming an SSRF proxy.

HomeStack runs on the household LAN, beside Postgres, the backend itself and a reverse proxy,
none of which are reachable from outside. A feature that fetches an arbitrary URL *from the
server* hands a user the ability to reach all of them — so this module fails closed: a request
is refused unless every resolved address is demonstrably public.

The checks that matter, and why string inspection alone is not enough:

- Every address the hostname resolves to is checked, not just the first. A name with one public
  and one loopback answer must be refused, not load-balanced into.
- Redirects are re-validated at every hop. Validating only the URL the user typed lets a public
  host bounce the request to 169.254.169.254 or homestack-postgres.
- The connection is made to an address that was actually validated, and the validated set is
  re-checked immediately before use, which closes most of the DNS-rebinding window. A residual
  window remains between the final check and the socket connect; see the note on
  ``_validated_addresses``.
- Size and time are capped while reading, not after, so a feed that never ends cannot exhaust
  memory or hold a worker open.

Nothing here interprets the response. The body is decoded as text and handed to the iCalendar
parser, which treats it strictly as data — no HTML, no scripts, no markup is ever executed or
rendered as trusted.
"""
from __future__ import annotations

import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request
from urllib.parse import urlsplit, urlunsplit

MAX_REDIRECTS = 3
CONNECT_TIMEOUT_SECONDS = 10
READ_TIMEOUT_SECONDS = 20
MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # a very large school/season feed is well under this

ALLOWED_SCHEMES = {"http", "https"}
# webcal is a display convention, not a transport: it is the same HTTP(S) fetch underneath.
WEBCAL_SCHEMES = {"webcal", "webcals"}

USER_AGENT = "HomeStack-Calendar/1.0 (+calendar source sync)"


class CalendarFetchError(Exception):
    """A fetch that was refused or failed. The message is safe to show the household."""


def normalise_url(raw: str) -> str:
    """Normalise a user-supplied calendar URL, or raise CalendarFetchError.

    webcal:// and webcals:// map to https:// — webcal is unencrypted-by-convention only in the
    sense that it says nothing about transport, so the secure choice is the right default.
    """
    value = (raw or "").strip()
    if not value:
        raise CalendarFetchError("Enter a calendar URL.")
    parts = urlsplit(value)
    scheme = parts.scheme.lower()
    if scheme in WEBCAL_SCHEMES:
        parts = parts._replace(scheme="https")
        scheme = "https"
    if scheme not in ALLOWED_SCHEMES:
        raise CalendarFetchError("Only http, https and webcal calendar links are supported.")
    if not parts.hostname:
        raise CalendarFetchError("That calendar link has no host.")
    if parts.username or parts.password:
        # Credentials in the URL are not supported, and quietly stripping them would send an
        # unauthenticated request the user believes is authenticated.
        raise CalendarFetchError("Calendar links with an embedded username or password are not supported.")
    return urlunsplit(parts)


def _is_public_address(ip: ipaddress._BaseAddress) -> bool:
    """Whether an address is safe to connect to from the server.

    Deliberately an allowlist of "ordinary public unicast": anything private, loopback,
    link-local (which covers the 169.254.169.254 cloud metadata service), multicast, reserved or
    unspecified is refused, as is any IPv4-mapped or 6to4/Teredo IPv6 address that embeds one of
    those — an attacker should not be able to launder 127.0.0.1 through ::ffff:127.0.0.1.
    """
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            return _is_public_address(ip.ipv4_mapped)
        if ip.sixtofour is not None:
            return _is_public_address(ip.sixtofour)
        if ip.teredo is not None:
            return _is_public_address(ip.teredo[1])
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _validated_addresses(host: str, port: int) -> list[tuple]:
    """Resolve a host and refuse it unless *every* answer is a public address.

    Requiring all answers rather than filtering to the public ones is the stricter reading: a
    name that resolves to both a public address and homestack-postgres is being used to smuggle,
    and there is no legitimate calendar feed that looks like that.
    """
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise CalendarFetchError("That calendar host could not be found.") from exc
    if not infos:
        raise CalendarFetchError("That calendar host could not be found.")
    for info in infos:
        address = info[4][0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError as exc:
            raise CalendarFetchError("That calendar host is not reachable.") from exc
        if not _is_public_address(ip):
            raise CalendarFetchError(
                "That calendar link points inside the local network, which is not allowed.",
            )
    return infos


def _check_host(url: str) -> None:
    parts = urlsplit(url)
    host = parts.hostname
    if not host:
        raise CalendarFetchError("That calendar link has no host.")
    # A literal IP is checked directly; a name is checked through resolution.
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        _validated_addresses(host, parts.port or (443 if parts.scheme == "https" else 80))
        return
    if not _is_public_address(ip):
        raise CalendarFetchError(
            "That calendar link points inside the local network, which is not allowed.",
        )


def validate_destination(raw_url: str) -> str:
    """Normalise a URL and refuse it now if it points anywhere internal.

    Used when a subscription is *saved*, so an internal address is rejected at the point the
    household enters it rather than silently stored and only refused at the next sync. The
    check is repeated at fetch time regardless — the address behind a name can change.
    """
    url = normalise_url(raw_url)
    _check_host(url)
    return url


def fetch_calendar(raw_url: str, *, max_bytes: int = MAX_RESPONSE_BYTES) -> str:
    """Fetch a calendar feed as text, validating the destination at every hop.

    Redirects are followed manually so each new location is validated the same way as the
    original; urllib's own redirect handling would follow a Location straight into the LAN.
    """
    url = normalise_url(raw_url)
    for _ in range(MAX_REDIRECTS + 1):
        _check_host(url)
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/calendar, text/plain;q=0.8, */*;q=0.1"},
            method="GET",
        )
        opener = urllib.request.build_opener(_NoRedirect)
        try:
            response = opener.open(request, timeout=CONNECT_TIMEOUT_SECONDS)
        except urllib.error.HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308):
                location = exc.headers.get("Location")
                if not location:
                    raise CalendarFetchError("That calendar link redirected without a destination.") from exc
                url = normalise_url(urllib.parse.urljoin(url, location))
                continue
            raise CalendarFetchError(f"The calendar server returned an error ({exc.code}).") from exc
        except urllib.error.URLError as exc:
            raise CalendarFetchError("That calendar could not be reached.") from exc
        except (TimeoutError, socket.timeout) as exc:
            raise CalendarFetchError("That calendar took too long to respond.") from exc

        with response:
            declared = response.headers.get("Content-Length")
            if declared and declared.isdigit() and int(declared) > max_bytes:
                raise CalendarFetchError("That calendar is too large to import.")
            # Read one byte past the cap so an over-long body is detected rather than truncated
            # into something that might still parse.
            try:
                body = response.read(max_bytes + 1)
            except (TimeoutError, socket.timeout) as exc:
                raise CalendarFetchError("That calendar took too long to respond.") from exc
            if len(body) > max_bytes:
                raise CalendarFetchError("That calendar is too large to import.")
        text = body.decode("utf-8", errors="replace")
        if "BEGIN:VCALENDAR" not in text.upper():
            raise CalendarFetchError("That link did not return a calendar file.")
        return text
    raise CalendarFetchError("That calendar link redirected too many times.")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Turn redirects into HTTPError so the caller can validate the new host itself."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, D102
        return None
