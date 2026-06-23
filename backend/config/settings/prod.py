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
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
