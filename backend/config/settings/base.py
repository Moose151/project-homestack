"""
Base settings shared by every environment.

Environment-specific overrides live in dev.py / prod.py / test.py. Select one with
DJANGO_SETTINGS_MODULE (defaults to config.settings.dev — see manage.py / wsgi / asgi).
"""
import os
from pathlib import Path

# config/settings/base.py -> parents[2] == backend/
BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-change-me")
DEBUG = False
ALLOWED_HOSTS: list[str] = [
    h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h
]

# --- CSRF trusted origins (Django 4+) ---
# Authenticated writes are CSRF-checked by DRF's SessionAuthentication, which verifies the
# browser's Origin header. The frontend dev proxy uses changeOrigin, so the backend's Host
# never equals the browser Origin — meaning the Origin must be trusted explicitly or every
# write 403s with "Origin checking failed". We derive the http/https origins (on the
# frontend port and the default port) for each allowed host, so adding your LAN address to
# DJANGO_ALLOWED_HOSTS is enough — no separate origin list to maintain. Extra full origins
# (incl. scheme) can still be supplied via DJANGO_CSRF_TRUSTED_ORIGINS.
_FRONTEND_PORT = os.environ.get("FRONTEND_PORT", "5173")
_CSRF_HOSTS = [
    h
    for h in os.environ.get(
        "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0,homestack-backend"
    ).split(",")
    if h and h != "*"
]
_derived_origins: list[str] = []
for _host in _CSRF_HOSTS:
    for _scheme in ("http", "https"):
        _derived_origins.append(f"{_scheme}://{_host}:{_FRONTEND_PORT}")
        _derived_origins.append(f"{_scheme}://{_host}")
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(
    [o for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o]
    + _derived_origins
))

# --- Applications ---
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
]

THIRD_PARTY_APPS = [
    "rest_framework",
]

# Modular-monolith apps (Architecture §5). Empty skeletons in Phase 1.1; node apps
# beyond atlas are added in their own milestones.
LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.people",
    "apps.permissions",
    "apps.nodes",
    "apps.hub",
    "apps.scheduling",  # calendar app is named `scheduling`, not `calendar` (D16)
    "apps.notifications",
    "apps.attachments",
    "apps.audit",
    "apps.search",
    "apps.backups",
    "apps.events",  # thin signal interface only (D4) — no broker, no event table
    "apps.atlas",
    "apps.meridian",  # Milestone 2 — native chores/points/rewards node (D13, D14)
]

INSTALLED_APPS = [
    *DJANGO_APPS,
    *THIRD_PARTY_APPS,
    *LOCAL_APPS,
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    # CSRF: DRF's SessionAuthentication enforces CSRF on authenticated unsafe requests,
    # so the cookie-issuing middleware must be present for the SPA to obtain a token.
    # DRF APIViews are csrf_exempt at the middleware level (DRF does its own check), so
    # this does not double-guard the login endpoints. The web/kiosk clients send the
    # token back via the X-CSRFToken header. (Session auth, D6.)
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

# --- Custom user model (D6) — set before any migration runs ---
AUTH_USER_MODEL = "accounts.User"

# --- Auth backends (D6): PIN first, password second ---
AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.PinBackend",
    "apps.accounts.backends.PasswordBackend",
]

# --- Session security ---
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_ENGINE = "django.contrib.sessions.backends.db"

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.debug",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --- Database ---
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "homestack"),
        "USER": os.environ.get("POSTGRES_USER", "homestack"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "homestack-postgres"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

# --- Password hashing (D6) ---
# Argon2id first, for both PINs and passwords once accounts land (Phase 1.3).
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

# --- Django REST Framework ---
# Session auth for web/kiosk (D6); token auth added with native apps. Default permission
# stays AllowAny until the central resolver lands (Phase 1.5, D10) — there are no
# protected endpoints yet. JSON only for now (browsable API needs contrib.auth).
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# --- I18N / TZ ---
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- Static ---
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Backups (D17) ---
# Docker maps backup_data volume to /app/backups; dev/test fall back to BASE_DIR/backups.
BACKUP_DIR = BASE_DIR / "backups"
MEDIA_ROOT = BASE_DIR / "media"
