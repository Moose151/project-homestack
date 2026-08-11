"""Small SSRF-resistant HTTP client for public product metadata and images."""
from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit


class LinkFetchError(ValueError):
    pass


@dataclass(frozen=True)
class FetchResult:
    url: str
    content: bytes
    content_type: str
    headers: dict[str, str]


def _normalise_url(raw_url: str) -> str:
    value = (raw_url or "").strip()
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise LinkFetchError("Enter a public http or https URL.")
    if parsed.username or parsed.password:
        raise LinkFetchError("URLs containing credentials are not allowed.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise LinkFetchError("That URL has an invalid port.") from exc
    if port not in {None, 80, 443}:
        raise LinkFetchError("Only standard web ports are allowed.")
    host = parsed.hostname.encode("idna").decode("ascii").lower()
    netloc = host
    if port and port != (443 if parsed.scheme.lower() == "https" else 80):
        netloc = f"{host}:{port}"
    return urlunsplit((parsed.scheme.lower(), netloc, parsed.path or "/", parsed.query, ""))


def _public_addresses(host: str, port: int) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise LinkFetchError("The website address could not be resolved.") from exc
    addresses: list[str] = []
    for info in infos:
        value = info[4][0]
        try:
            address = ipaddress.ip_address(value)
        except ValueError as exc:
            raise LinkFetchError("The website resolved to an invalid address.") from exc
        if not address.is_global:
            raise LinkFetchError("Private, local and reserved network addresses are not allowed.")
        if value not in addresses:
            addresses.append(value)
    if not addresses:
        raise LinkFetchError("The website address could not be resolved.")
    return addresses


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, hostname: str, ip: str, port: int, timeout: float):
        super().__init__(hostname, port=port, timeout=timeout, context=ssl.create_default_context())
        self._pinned_ip = ip

    def connect(self) -> None:
        sock = socket.create_connection((self._pinned_ip, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def fetch_public(
    raw_url: str,
    *,
    accepted_types: tuple[str, ...] = ("text/html", "application/xhtml+xml"),
    max_bytes: int = 2_000_000,
    timeout: float = 8.0,
    max_redirects: int = 4,
) -> FetchResult:
    url = _normalise_url(raw_url)
    for redirect_count in range(max_redirects + 1):
        parsed = urlsplit(url)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        ip = _public_addresses(parsed.hostname or "", port)[0]
        if parsed.scheme == "https":
            connection = _PinnedHTTPSConnection(parsed.hostname or "", ip, port, timeout)
        else:
            connection = http.client.HTTPConnection(ip, port=port, timeout=timeout)
        target = parsed.path or "/"
        if parsed.query:
            target += f"?{parsed.query}"
        host_header = parsed.hostname or ""
        if parsed.port and parsed.port not in {80, 443}:
            host_header += f":{parsed.port}"
        try:
            connection.request("GET", target, headers={
                "Host": host_header,
                "User-Agent": "HomeStack-LinkPreview/1.0 (+self-hosted household app)",
                "Accept": "text/html,application/xhtml+xml,image/*;q=0.8",
                "Accept-Encoding": "identity",
                "Connection": "close",
            })
            response = connection.getresponse()
            headers = {key.lower(): value for key, value in response.getheaders()}
            if response.status in {301, 302, 303, 307, 308}:
                location = headers.get("location")
                if not location or redirect_count >= max_redirects:
                    raise LinkFetchError("The website redirected too many times.")
                url = _normalise_url(urljoin(url, location))
                continue
            if response.status < 200 or response.status >= 300:
                raise LinkFetchError(f"The website returned HTTP {response.status}.")
            declared_length = headers.get("content-length")
            if declared_length:
                try:
                    if int(declared_length) > max_bytes:
                        raise LinkFetchError("The website response is too large.")
                except ValueError:
                    pass
            content_type = headers.get("content-type", "").split(";", 1)[0].strip().lower()
            if not any(content_type == allowed or content_type.startswith(f"{allowed}/") for allowed in accepted_types):
                raise LinkFetchError("The website returned an unsupported content type.")
            content = response.read(max_bytes + 1)
            if len(content) > max_bytes:
                raise LinkFetchError("The website response is too large.")
            return FetchResult(url=url, content=content, content_type=content_type, headers=headers)
        except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
            raise LinkFetchError("The website could not be reached safely.") from exc
        finally:
            connection.close()
    raise LinkFetchError("The website redirected too many times.")
