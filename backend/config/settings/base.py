"""
Base settings shared by every environment.

Environment-specific overrides live in dev.py / prod.py / test.py. Select one with
DJANGO_SETTINGS_MODULE (defaults to config.settings.dev — see manage.py / wsgi / asgi).

NOTE (D6 / custom user): Django's contrib auth, sessions, messages and admin apps are
deliberately NOT installed yet. They are added in Phase 1.3 together with the custom
`accounts.User`, so that AUTH_USER_MODEL is in place BEFORE the first migration and we
never have to swap away from Django's default user model. No migrations are run in 1.1.
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

# --- Applications ---
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
]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    *THIRD_PARTY_APPS,
    *LOCAL_APPS,
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    # SessionMiddleware + AuthenticationMiddleware are added with auth in Phase 1.3.
]

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
