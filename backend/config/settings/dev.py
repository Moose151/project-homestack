"""Development settings: local home server, hot reload, permissive hosts."""
import os

from .base import *  # noqa: F401,F403
from .base import CSRF_TRUSTED_ORIGINS as _ENV_CSRF_TRUSTED_ORIGINS

DEBUG = True

# Includes the compose service name so the frontend dev proxy (changeOrigin) is accepted.
ALLOWED_HOSTS = [
    h
    for h in os.environ.get(
        "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0,homestack-backend"
    ).split(",")
    if h
]

# Auto-derive trusted CSRF origins from the allowed hosts on the dev frontend/backend ports,
# so a LAN deployment only needs to add its server IP to DJANGO_ALLOWED_HOSTS — writes then
# work without separately maintaining DJANGO_CSRF_TRUSTED_ORIGINS. Explicit env entries (e.g.
# an https reverse-proxy origin) are merged in and take effect too.
_FRONTEND_PORT = os.environ.get("FRONTEND_PORT", "5173")
_BACKEND_PORT = os.environ.get("BACKEND_PORT", "8000")
_DEV_PORTS = {_FRONTEND_PORT, _BACKEND_PORT, "5173", "8000"}
_DEV_HOSTS = [h for h in ALLOWED_HOSTS if h and h != "0.0.0.0"]
CSRF_TRUSTED_ORIGINS = sorted(
    {
        *_ENV_CSRF_TRUSTED_ORIGINS,
        *(f"http://{h}:{p}" for h in _DEV_HOSTS for p in _DEV_PORTS),
        # Behind a reverse proxy the browser Origin carries no port (e.g.
        # http://homestack.home.arpa). Trust both schemes for every allowed host so a LAN
        # deploy only needs its hostname added to DJANGO_ALLOWED_HOSTS — nothing else.
        *(f"http://{h}" for h in _DEV_HOSTS),
        *(f"https://{h}" for h in _DEV_HOSTS),
    }
)
