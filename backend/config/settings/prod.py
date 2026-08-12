"""
Production settings: self-hosted on the home server, behind Nginx Proxy Manager.

This is the live path. The production Compose file pins DJANGO_SETTINGS_MODULE to this module in
its `environment:` block — which takes precedence over `.env` — so a stale `DJANGO_SETTINGS_MODULE`
left over from development cannot silently put the live server back on development settings.

HomeStack remains LAN-only. Public exposure is a separate, still-closed gate
(docs/05_Security_Architecture_Document.md §14).
"""
import os

from .base import *  # noqa: F401,F403
from .base import ALLOWED_HOSTS as _ENV_ALLOWED_HOSTS
from .base import CSRF_TRUSTED_ORIGINS as _ENV_CSRF_TRUSTED_ORIGINS
from .base import MIDDLEWARE as _BASE_MIDDLEWARE

DEBUG = False

# The hostname Nginx Proxy Manager holds the certificate for and proxies to this container.
PUBLIC_HOSTNAME = os.environ.get("HOMESTACK_PUBLIC_HOSTNAME", "").strip()

# `localhost`/`127.0.0.1` are always allowed so the container's own health check can reach the
# health endpoint without every deployment having to remember them. They only ever match a request
# that already arrived at this container; real ingress is still restricted to the explicit list.
ALLOWED_HOSTS = sorted(
    {
        *_ENV_ALLOWED_HOSTS,
        *([PUBLIC_HOSTNAME] if PUBLIC_HOSTNAME else []),
        "localhost",
        "127.0.0.1",
    }
)

# Django checks the Origin header of every write against this list *after* first accepting an
# Origin that matches the one it derives from Host + the proxy scheme — which is why writes still
# work behind NPM with this empty. Deriving the public hostname anyway means the deployment does
# not silently depend on the proxy preserving Host. Explicit entries still apply, and nothing
# broader is inferred: unlike dev, prod never wildcards a domain or trusts plain http.
CSRF_TRUSTED_ORIGINS = sorted(
    {
        *_ENV_CSRF_TRUSTED_ORIGINS,
        *([f"https://{PUBLIC_HOSTNAME}"] if PUBLIC_HOSTNAME else []),
    }
)

# TLS terminates at NPM, so the request reaches this container over plain HTTP on the LAN with the
# original scheme in X-Forwarded-Proto. Without this, Django would consider every request insecure
# and refuse to set the secure cookies configured below.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Secure cookies require HTTPS to be sent at all. The live deployment is HTTPS via NPM, so this
# stays on; DJANGO_SECURE_COOKIES=0 exists only for a deliberately plain-HTTP LAN deployment,
# where secure cookies would otherwise make login fail silently.
_SECURE_COOKIES = os.environ.get("DJANGO_SECURE_COOKIES", "1") != "0"
SESSION_COOKIE_SECURE = _SECURE_COOKIES
CSRF_COOKIE_SECURE = _SECURE_COOKIES

# --- Static files (Django admin CSS/JS) ---
# With DEBUG=False Django stops serving /static/ itself. WhiteNoise serves the collected files
# from the same gunicorn process, which keeps Django's admin styled without standing up a second
# static-serving architecture just for it. It serves STATIC_ROOT only — never MEDIA_ROOT, which
# stays behind the permission-checked attachment download path (D11).
# Inserted by position rather than hardcoded index so reordering base.py cannot silently move
# WhiteNoise somewhere it does not belong — it must sit directly after SecurityMiddleware.
MIDDLEWARE = list(_BASE_MIDDLEWARE)
MIDDLEWARE.insert(
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)

# Hashed filenames + a manifest, so admin assets can be cached hard and still update on redeploy.
# Requires `collectstatic` to have run — the backend image does this at build time.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
