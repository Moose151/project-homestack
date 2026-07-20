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

# Django 4+ verifies the Origin header of unsafe (POST/PATCH/DELETE) requests against this
# list. Because the SPA is served from a different port than the API and the Vite dev proxy
# rewrites the Host header (changeOrigin), the browser Origin (e.g. http://192.168.1.125:5173)
# must be listed explicitly or every write fails with "CSRF Failed: Origin checking failed".
# Provide a comma-separated list of scheme://host[:port] entries. dev.py also auto-derives
# entries from DJANGO_ALLOWED_HOSTS so a LAN deployment only needs to set the host.
CSRF_TRUSTED_ORIGINS: list[str] = [
    o.strip()
    for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if o.strip()
]

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
    "apps.achievements",  # Milestone 2 — cross-node badges, event-driven (D20)
    "apps.education",  # Milestone 3 — school/university tracking (uni-first V1 slice)
    "apps.books",  # Books node — personal reading shelves and shared book clubs
    "apps.home_wiki",  # Milestone 3 — household knowledge base (Node Spec 12)
    "apps.pets",  # Milestone 3 — pet profiles, treatments, vet appointments (Node Spec 13)
    "apps.homestead",  # Home/property hub — maintenance, appliances, providers, improvements (Node Spec 25)
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

# --- Media (user uploads) ---
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Backups (D17) ---
# Docker maps backup_data volume to /app/backups; dev/test fall back to BASE_DIR/backups.
BACKUP_DIR = BASE_DIR / "backups"
