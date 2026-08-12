"""Production-serving configuration tests (docs/34_Recommended_Next_Steps.md §3).

These guard the settings the live deployment depends on but that no ordinary feature test would
ever exercise, because the whole suite runs under `config.settings.test`. A regression here does
not fail a request in CI — it fails the household's server after a deploy, which is exactly the
class of mistake worth a test.
"""
from __future__ import annotations

import importlib
import os
from unittest import mock

from django.core.checks import Error, Warning
from django.test import SimpleTestCase

from apps.core.checks import PLACEHOLDER_SECRET_KEY, check_production_configuration

# A plausible live environment: the real .env shape from HANDOVER.md §2.
_LIVE_ENV = {
    "DJANGO_SECRET_KEY": "a-real-generated-secret",
    "DJANGO_ALLOWED_HOSTS": "192.168.1.125,homestack.moosesoftwares.com",
    "HOMESTACK_PUBLIC_HOSTNAME": "homestack.moosesoftwares.com",
    "DJANGO_CSRF_TRUSTED_ORIGINS": "",
    "DJANGO_SECURE_COOKIES": "1",
}


def _load_prod_settings(**overrides):
    """Import config.settings.prod against a controlled environment.

    Settings modules read os.environ at import time, so a reload under a patched environment is
    the only way to observe what a given .env would actually produce. base must be reloaded first
    because prod reads the env-derived values off it, and it was imported once at process start.
    """
    env = {**_LIVE_ENV, **overrides}
    with mock.patch.dict(os.environ, env, clear=False):
        importlib.reload(importlib.import_module("config.settings.base"))
        return importlib.reload(importlib.import_module("config.settings.prod"))


class ProductionSettingsTests(SimpleTestCase):
    def test_debug_is_off_regardless_of_the_environment(self):
        # DJANGO_DEBUG=1 is the .env default for development and is very likely still set on a
        # server that has only ever run dev settings.
        prod = _load_prod_settings(DJANGO_DEBUG="1")
        self.assertFalse(prod.DEBUG)

    def test_public_hostname_is_allowed_and_csrf_trusted_without_extra_env(self):
        prod = _load_prod_settings()
        self.assertIn("homestack.moosesoftwares.com", prod.ALLOWED_HOSTS)
        self.assertIn("https://homestack.moosesoftwares.com", prod.CSRF_TRUSTED_ORIGINS)

    def test_csrf_derivation_never_trusts_plain_http_or_a_wildcard(self):
        # Development settings deliberately wildcard .home.arpa/.local and trust http://; prod
        # must not inherit that leniency by accident.
        prod = _load_prod_settings()
        for origin in prod.CSRF_TRUSTED_ORIGINS:
            self.assertTrue(origin.startswith("https://"), origin)
            self.assertNotIn("*", origin)

    def test_explicit_csrf_origins_are_kept_alongside_the_derived_one(self):
        prod = _load_prod_settings(DJANGO_CSRF_TRUSTED_ORIGINS="https://other.example")
        self.assertIn("https://other.example", prod.CSRF_TRUSTED_ORIGINS)
        self.assertIn("https://homestack.moosesoftwares.com", prod.CSRF_TRUSTED_ORIGINS)

    def test_loopback_is_allowed_so_the_container_health_check_works(self):
        prod = _load_prod_settings()
        self.assertIn("127.0.0.1", prod.ALLOWED_HOSTS)

    def test_cookies_are_secure_behind_the_proxy_by_default(self):
        prod = _load_prod_settings()
        self.assertTrue(prod.SESSION_COOKIE_SECURE)
        self.assertTrue(prod.CSRF_COOKIE_SECURE)
        self.assertEqual(prod.SECURE_PROXY_SSL_HEADER, ("HTTP_X_FORWARDED_PROTO", "https"))

    def test_plain_http_lan_deployments_can_still_opt_out(self):
        prod = _load_prod_settings(DJANGO_SECURE_COOKIES="0")
        self.assertFalse(prod.SESSION_COOKIE_SECURE)
        self.assertFalse(prod.CSRF_COOKIE_SECURE)

    def test_whitenoise_sits_directly_after_the_security_middleware(self):
        prod = _load_prod_settings()
        index = prod.MIDDLEWARE.index("whitenoise.middleware.WhiteNoiseMiddleware")
        self.assertEqual(prod.MIDDLEWARE[index - 1], "django.middleware.security.SecurityMiddleware")

    def test_static_storage_is_hashed_and_media_storage_is_not_public(self):
        prod = _load_prod_settings()
        self.assertEqual(
            prod.STORAGES["staticfiles"]["BACKEND"],
            "whitenoise.storage.CompressedManifestStaticFilesStorage",
        )
        # WhiteNoise serves STATIC_ROOT only. Uploads stay behind the permission-checked
        # attachment download path (D11) and must never gain a static URL prefix.
        self.assertNotEqual(prod.STATIC_ROOT, prod.MEDIA_ROOT)


class ProductionCheckTests(SimpleTestCase):
    """The checks themselves, driven directly — the suite runs under test settings, so
    `_is_production()` is patched rather than faking a settings module."""

    def _run(self, **settings_overrides) -> list:
        with mock.patch("apps.core.checks._is_production", return_value=True), \
                self.settings(**settings_overrides):
            return check_production_configuration(None)

    def _ids(self, problems) -> set[str]:
        return {problem.id for problem in problems}

    def _healthy(self) -> dict:
        return {
            "ALLOWED_HOSTS": ["homestack.moosesoftwares.com"],
            "CSRF_TRUSTED_ORIGINS": ["https://homestack.moosesoftwares.com"],
            "SECRET_KEY": "a-real-generated-secret",
            "DEBUG": False,
            "SESSION_COOKIE_SECURE": True,
            "CSRF_COOKIE_SECURE": True,
        }

    def test_a_correct_production_environment_reports_nothing(self):
        self.assertEqual(self._run(**self._healthy()), [])

    def test_empty_allowed_hosts_is_an_error(self):
        problems = self._run(**{**self._healthy(), "ALLOWED_HOSTS": []})
        self.assertIn("homestack.E001", self._ids(problems))
        self.assertTrue(all(isinstance(p, Error) for p in problems))

    def test_loopback_only_allowed_hosts_is_an_error(self):
        # The realistic shape of the mistake: prod always adds localhost/127.0.0.1 for the health
        # check, so a missing DJANGO_ALLOWED_HOSTS leaves a list that is non-empty but useless.
        problems = self._run(**{**self._healthy(), "ALLOWED_HOSTS": ["localhost", "127.0.0.1"]})
        self.assertIn("homestack.E001", self._ids(problems))

    def test_empty_csrf_trusted_origins_warns_but_does_not_block(self):
        # Verified against a real gunicorn container: writes still succeed behind the proxy,
        # because Django accepts the origin it derives from Host + X-Forwarded-Proto. Making
        # this an Error would block a deployment that works.
        problems = self._run(**{**self._healthy(), "CSRF_TRUSTED_ORIGINS": []})
        self.assertEqual(self._ids(problems), {"homestack.W002"})
        self.assertTrue(all(isinstance(p, Warning) for p in problems))

    def test_the_committed_placeholder_secret_key_is_an_error(self):
        problems = self._run(**{**self._healthy(), "SECRET_KEY": PLACEHOLDER_SECRET_KEY})
        self.assertIn("homestack.E003", self._ids(problems))

    def test_debug_enabled_is_an_error(self):
        problems = self._run(**{**self._healthy(), "DEBUG": True})
        self.assertIn("homestack.E004", self._ids(problems))

    def test_insecure_cookies_warn_rather_than_block(self):
        # A plain-HTTP LAN deployment is a supported (if discouraged) choice, so this must not
        # stop a deployment the way the errors above do.
        problems = self._run(**{**self._healthy(), "SESSION_COOKIE_SECURE": False})
        self.assertEqual(self._ids(problems), {"homestack.W001"})
        self.assertTrue(all(isinstance(p, Warning) for p in problems))

    def test_checks_are_silent_outside_production_settings(self):
        # Runs unpatched, under config.settings.test — development must never be nagged.
        self.assertEqual(check_production_configuration(None), [])
