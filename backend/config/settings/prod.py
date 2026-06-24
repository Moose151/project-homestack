"""
Production settings: self-hosted, behind a reverse proxy on the home server.

Hardening here is intentionally minimal for now; the full pre-exposure checklist
(HTTPS, reverse proxy, rate limiting, etc.) is Milestone 4 / Security doc §14. Do not
expose publicly until that checklist is satisfied.
"""
import os

from .base import *  # noqa: F401,F403

DEBUG = False

# Required in prod — fail loudly if unset rather than defaulting to something insecure.
ALLOWED_HOSTS = [
    h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h
]

# Trust the reverse proxy's X-Forwarded-Proto once TLS terminates there (M4).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Secure cookies require HTTPS to be sent at all. Until TLS lands (M4) the home
# server runs plain HTTP on the LAN, where secure cookies would silently break login.
# Defaults to secure; set DJANGO_SECURE_COOKIES=0 for a plain-HTTP LAN deployment.
_SECURE_COOKIES = os.environ.get("DJANGO_SECURE_COOKIES", "1") != "0"
SESSION_COOKIE_SECURE = _SECURE_COOKIES
CSRF_COOKIE_SECURE = _SECURE_COOKIES
