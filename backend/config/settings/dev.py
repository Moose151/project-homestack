"""Development settings: local home server, hot reload, permissive hosts."""
import os

from .base import *  # noqa: F401,F403

DEBUG = True

# Includes the compose service name so the frontend dev proxy (changeOrigin) is accepted.
ALLOWED_HOSTS = [
    h
    for h in os.environ.get(
        "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0,homestack-backend"
    ).split(",")
    if h
]
