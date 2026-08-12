"""Deployment configuration checks for the production settings module.

These run as ordinary Django system checks, so any management command surfaces them. The deployment
sequence invokes them deliberately — `docker compose run --rm --no-deps homestack-backend
manage.py check` against the newly built image — *before* `docker compose up -d` promotes it. A
misconfigured live environment therefore fails while the previous containers are still serving,
when abandoning the deploy costs nothing (docs/35_Production_Serving_and_Deployment.md §11.2).

Gunicorn does not run system checks when it imports `config.wsgi`, which is deliberate: a stale
value surfaces as a failed deployment command rather than crash-looping a container that is
already live.

They only fire under `config.settings.prod`. Development and test settings are deliberately
permissive and must not be nagged about production concerns.

Each check guards a failure that is silent, or nearly silent, in production:

- loopback-only ALLOWED_HOSTS → every household request 400s with no useful browser-side
  explanation, even though the container's own health check keeps passing;
- the placeholder SECRET_KEY → every existing session silently survives a key that is in Git;
- empty CSRF_TRUSTED_ORIGINS → writes still work in the normal proxy setup (see below), but the
  deployment has no margin if the proxy stops preserving the Host header;
- insecure cookies on an HTTPS deployment → session/CSRF cookies exposed to plain HTTP.

Note on CSRF, verified against a real gunicorn container rather than assumed: Django accepts a
write when the browser's Origin equals the origin it derives from `Host` plus the scheme from
SECURE_PROXY_SSL_HEADER. Nginx Proxy Manager forwards the household hostname unchanged, so a
same-origin write from the SPA passes with CSRF_TRUSTED_ORIGINS empty. That makes an empty list a
*warning*, never an error — treating it as fatal would block a deployment that works.
"""
from __future__ import annotations

from django.conf import settings
from django.core.checks import Error, Warning, register

# The value base.py falls back to when DJANGO_SECRET_KEY is unset. It is in the repository, so it
# is public by definition and must never reach a real deployment.
PLACEHOLDER_SECRET_KEY = "dev-insecure-change-me"

PRODUCTION_SETTINGS_MODULE = "config.settings.prod"

# prod.py always allows these so the container health check can reach the health endpoint. They
# say nothing about whether the deployment is reachable by an actual household browser, so a
# hosts list consisting of only these is still a broken deployment.
LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1"})


def _is_production() -> bool:
    return settings.SETTINGS_MODULE == PRODUCTION_SETTINGS_MODULE


@register("homestack_deployment")
def check_production_configuration(app_configs, **kwargs) -> list:
    if not _is_production():
        return []

    problems: list = []

    if not set(settings.ALLOWED_HOSTS) - LOOPBACK_HOSTS:
        problems.append(Error(
            "ALLOWED_HOSTS names no host beyond loopback under production settings.",
            hint=(
                "Set DJANGO_ALLOWED_HOSTS in .env to the hostnames this server answers on, "
                "e.g. '192.168.1.125,homestack.moosesoftwares.com' (HOMESTACK_PUBLIC_HOSTNAME "
                "is added automatically). Household requests are otherwise rejected with "
                "HTTP 400 while the container health check still passes."
            ),
            id="homestack.E001",
        ))

    if not settings.CSRF_TRUSTED_ORIGINS:
        problems.append(Warning(
            "CSRF_TRUSTED_ORIGINS is empty under production settings.",
            hint=(
                "Writes still succeed while the proxy forwards the household hostname unchanged, "
                "because Django derives that origin from Host + X-Forwarded-Proto. Set "
                "HOMESTACK_PUBLIC_HOSTNAME (prod derives https://<hostname> from it) so the "
                "deployment does not depend on that alone."
            ),
            id="homestack.W002",
        ))

    if settings.SECRET_KEY == PLACEHOLDER_SECRET_KEY:
        problems.append(Error(
            "DJANGO_SECRET_KEY is still the placeholder value committed to the repository.",
            hint=(
                "Generate one with: "
                "python -c \"import secrets; print(secrets.token_urlsafe(64))\" "
                "and set DJANGO_SECRET_KEY in .env."
            ),
            id="homestack.E003",
        ))

    if settings.DEBUG:
        problems.append(Error(
            "DEBUG is enabled under production settings.",
            hint="config.settings.prod hardcodes DEBUG=False; something has overridden it.",
            id="homestack.E004",
        ))

    if not (settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE):
        problems.append(Warning(
            "Session/CSRF cookies are not marked secure.",
            hint=(
                "Expected on a deliberately plain-HTTP LAN deployment (DJANGO_SECURE_COOKIES=0). "
                "If this server is behind Nginx Proxy Manager HTTPS, unset it — cookies are "
                "otherwise sent over plain HTTP too."
            ),
            id="homestack.W001",
        ))

    return problems
