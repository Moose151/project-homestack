"""Fetching a user-supplied calendar URL from the server, without becoming an SSRF proxy.

HomeStack runs on the household LAN, beside Postgres, the backend itself and a reverse proxy,
none of which are reachable from outside. A feature that fetches an arbitrary URL *from the
server* hands a user the ability to reach all of them — so this module fails closed.

The central rule is that **the socket connects to an address this module already validated**.
Resolving a hostname, approving the answer, and then handing the *hostname* to an HTTP library
would let that library resolve it a second time and connect somewhere else entirely: classic
DNS rebinding, against which pre-validation is worthless. So the flow is always:

    resolve once  ->  validate every answer  ->  connect the socket to one validated address

For HTTPS the hostname is still used for everything it must be used for — SNI, certificate
verification, and the ``Host`` header — while only the TCP destination is pinned. Pinning
therefore costs nothing in TLS security: a certificate valid for the hostname is still required.

Redirects repeat the whole cycle. Each hop is resolved, validated and pinned independently,
because a public host that 302s to 169.254.169.254 is precisely the attack this exists to stop.

Nothing here interprets the response. The body is decoded as text and handed to the iCalendar
parser, which treats it strictly as data — no HTML, no scripts, no markup is ever executed or
rendered as trusted.
"""
from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from urllib.parse import urljoin, urlsplit, urlunsplit

MAX_REDIRECTS = 3
CONNECT_TIMEOUT_SECONDS = 10
MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # a very large school/season feed is well under this

ALLOWED_SCHEMES = {"http", "https"}
# webcal is a display convention, not a transport: it is the same HTTP(S) fetch underneath.
WEBCAL_SCHEMES = {"webcal", "webcals"}

USER_AGENT = "HomeStack-Calendar/1.0 (+calendar source sync)"

_REDIRECT_CODES = {301, 302, 303, 307, 308}


class CalendarFetchError(Exception):
    """A fetch that was refused or failed. The message is safe to show the household."""


def normalise_url(raw: str) -> str:
    """Normalise a user-supplied calendar URL, or raise CalendarFetchError.

    webcal:// and webcals:// map to https:// — webcal says nothing about transport, so the
    secure choice is the right default.
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

    Deliberately "ordinary public unicast only": anything private, loopback, link-local (which
    covers the 169.254.169.254 cloud metadata service), multicast, reserved or unspecified is
    refused, as is any IPv4-mapped or 6to4/Teredo IPv6 address that embeds one of those — an
    attacker must not be able to launder 127.0.0.1 through ::ffff:127.0.0.1.
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


def resolve_public_address(host: str, port: int) -> str:
    """Resolve a host **once** and return the validated address to connect to.

    Every answer must be public, not merely the one that gets picked: a name resolving to both a
    public address and homestack-postgres is being used to smuggle, and no legitimate calendar
    feed looks like that. Returning the address — rather than merely approving the name — is
    what allows the caller to connect without ever resolving again.
    """
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        # A literal address needs no resolution; validate it directly.
        if not _is_public_address(literal):
            raise CalendarFetchError(
                "That calendar link points inside the local network, which is not allowed.",
            )
        return host

    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise CalendarFetchError("That calendar host could not be found.") from exc
    if not infos:
        raise CalendarFetchError("That calendar host could not be found.")

    chosen: str | None = None
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
        if chosen is None:
            chosen = address
    return chosen


def _port_for(parts) -> int:
    if parts.port:
        return parts.port
    return 443 if parts.scheme == "https" else 80


def validate_destination(raw_url: str) -> str:
    """Normalise a URL and refuse it now if it points anywhere internal.

    Used when a subscription is *saved*, so an internal address is rejected at the point the
    household enters it rather than being stored and refused later. The check is repeated at
    fetch time regardless — the address behind a name can change between the two.
    """
    url = normalise_url(raw_url)
    parts = urlsplit(url)
    resolve_public_address(parts.hostname, _port_for(parts))
    return url


class _PinnedHTTPConnection(http.client.HTTPConnection):
    """Plain HTTP to a pre-validated address.

    ``self.host`` stays the original hostname so ``Host:`` is right; only the socket's
    destination is replaced.
    """

    def __init__(self, host, port, *, pinned_ip, timeout):
        super().__init__(host, port, timeout=timeout)
        self._pinned_ip = pinned_ip

    def connect(self):
        self.sock = socket.create_connection((self._pinned_ip, self.port), self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPS to a pre-validated address, with the hostname preserved where it matters.

    The socket goes to ``pinned_ip``; SNI and certificate verification both use ``self.host``,
    as does ``Host:``. So the destination is pinned without weakening TLS at all.
    """

    def __init__(self, host, port, *, pinned_ip, timeout, context=None):
        super().__init__(
            host, port, timeout=timeout, context=context or ssl.create_default_context(),
        )
        self._pinned_ip = pinned_ip

    def connect(self):
        sock = socket.create_connection((self._pinned_ip, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def _open(url: str, timeout: int):
    """One request to one validated, pinned address. Returns (connection, response)."""
    parts = urlsplit(url)
    host = parts.hostname
    port = _port_for(parts)
    pinned_ip = resolve_public_address(host, port)

    factory = _PinnedHTTPSConnection if parts.scheme == "https" else _PinnedHTTPConnection
    connection = factory(host, port, pinned_ip=pinned_ip, timeout=timeout)
    target = parts.path or "/"
    if parts.query:
        target = f"{target}?{parts.query}"
    default_port = 443 if parts.scheme == "https" else 80
    try:
        connection.request(
            "GET",
            target,
            headers={
                "Host": host if port == default_port else f"{host}:{port}",
                "User-Agent": USER_AGENT,
                "Accept": "text/calendar, text/plain;q=0.8, */*;q=0.1",
                "Connection": "close",
            },
        )
        return connection, connection.getresponse()
    except (TimeoutError, socket.timeout) as exc:
        connection.close()
        raise CalendarFetchError("That calendar took too long to respond.") from exc
    except (ssl.SSLError, ssl.CertificateError) as exc:
        connection.close()
        raise CalendarFetchError("That calendar's security certificate could not be verified.") from exc
    except (OSError, http.client.HTTPException) as exc:
        connection.close()
        raise CalendarFetchError("That calendar could not be reached.") from exc


def fetch_calendar(raw_url: str, *, max_bytes: int = MAX_RESPONSE_BYTES) -> str:
    """Fetch a calendar feed as text, resolving/validating/pinning at every hop."""
    url = normalise_url(raw_url)
    for _ in range(MAX_REDIRECTS + 1):
        connection, response = _open(url, CONNECT_TIMEOUT_SECONDS)
        try:
            if response.status in _REDIRECT_CODES:
                location = response.getheader("Location")
                if not location:
                    raise CalendarFetchError("That calendar link redirected without a destination.")
                # Normalised here, then resolved/validated/pinned afresh on the next pass.
                url = normalise_url(urljoin(url, location))
                continue
            if response.status != 200:
                raise CalendarFetchError(
                    f"The calendar server returned an error ({response.status}).",
                )

            declared = response.getheader("Content-Length")
            if declared and declared.isdigit() and int(declared) > max_bytes:
                raise CalendarFetchError("That calendar is too large to import.")
            try:
                # One byte past the cap, so an over-long body is detected rather than truncated
                # into something that might still parse.
                body = response.read(max_bytes + 1)
            except (TimeoutError, socket.timeout) as exc:
                raise CalendarFetchError("That calendar took too long to respond.") from exc
            if len(body) > max_bytes:
                raise CalendarFetchError("That calendar is too large to import.")
        finally:
            connection.close()

        text = body.decode("utf-8", errors="replace")
        if "BEGIN:VCALENDAR" not in text.upper():
            raise CalendarFetchError("That link did not return a calendar file.")
        return text
    raise CalendarFetchError("That calendar link redirected too many times.")
