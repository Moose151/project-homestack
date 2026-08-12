"""Friendly push-device naming from the browser's User-Agent (docs/32 §4).

Kept out of push.py so the pywebpush/VAPID mechanics stay focused on delivery, and out of the
frontend so every client that registers a subscription gets the same name (D3, API-first).

This is deliberately a small, honest heuristic, not a User-Agent database. It answers "which
browser, on roughly what kind of machine" — enough for a household member to recognise their own
device in a list. It does not attempt distro/version detection: a Firefox-on-Fedora User-Agent
only ever says "Linux", so claiming "Fedora" would be a guess. Anyone who wants more specific
naming renames the device, which is the point of the rename flow.
"""
from __future__ import annotations

# Ordered longest-match-first: Edge/Opera/Samsung all also contain "Chrome", and Chrome on iOS
# ("CriOS") / Firefox on iOS ("FxiOS") both also contain "Safari".
_BROWSERS: tuple[tuple[str, str], ...] = (
    ("Edg", "Edge"),
    ("OPR", "Opera"),
    ("Opera", "Opera"),
    ("SamsungBrowser", "Samsung Internet"),
    ("Vivaldi", "Vivaldi"),
    ("Brave", "Brave"),
    ("CriOS", "Chrome"),
    ("FxiOS", "Firefox"),
    ("Firefox", "Firefox"),
    ("Chromium", "Chromium"),
    ("Chrome", "Chrome"),
    ("Safari", "Safari"),
)

# Ordered so the more specific token wins: Android User-Agents also contain "Linux", and iPad/
# iPhone both sit under "Mac OS X" in modern Safari strings.
_PLATFORMS: tuple[tuple[str, str], ...] = (
    ("iPhone", "iPhone"),
    ("iPad", "iPad"),
    ("Android", "Android"),
    ("CrOS", "ChromeOS"),
    ("Windows", "Windows"),
    ("Macintosh", "Mac"),
    ("Mac OS X", "Mac"),
    ("Linux", "Linux"),
)


def parse_user_agent(user_agent: str) -> tuple[str, str]:
    """Return `(browser, platform)`, either of which may be `""` when nothing matches."""
    ua = user_agent or ""
    browser = next((name for token, name in _BROWSERS if token in ua), "")
    platform = next((name for token, name in _PLATFORMS if token in ua), "")
    return browser, platform


def default_label(browser: str, platform: str) -> str:
    """The generated friendly name, e.g. "Chrome on Android" or "Firefox on Linux".

    Falls back to whichever half is known, and finally to a generic name — never blank, so the
    device list always has something to show before the owner renames it.
    """
    if browser and platform:
        return f"{browser} on {platform}"
    return browser or platform or "New device"


def describe(user_agent: str) -> tuple[str, str, str]:
    """Convenience for the registration path: `(browser, platform, default_label)`."""
    browser, platform = parse_user_agent(user_agent)
    return browser, platform, default_label(browser, platform)
