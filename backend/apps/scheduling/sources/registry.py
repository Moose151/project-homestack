"""Which calendar sources exist, and what settings each one accepts.

Every source is a (kind, provider) pair registered here with a settings validator. Nothing
outside this registry can be created, and ``settings_json`` is never stored unvalidated —
those values decide what the server fetches and which jurisdiction's dates are produced, so
they are checked exactly like any other request input.

Adding a country or a school system later is a new provider module plus one entry here; it is
not a change to the Calendar page, the model, or the sync loop.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.scheduling.models import CalendarSource

# --- settings validators -------------------------------------------------------------------


def _bool(value, default: bool) -> bool:
    return bool(value) if isinstance(value, bool) else default


def _validate_holidays(settings: dict) -> dict:
    """Which jurisdiction levels this household wants.

    The jurisdiction itself comes from the household's configured location, not from settings —
    a source must not be able to claim a different state than the household is in.

    ``include_national`` is deliberately absent. It never had any effect (Australia has no
    separate national holiday list — see au_holidays) and a switch that does nothing is worse
    than no switch. A saved settings object still carrying it is accepted and the key is simply
    dropped, so an existing source keeps working without a migration.
    """
    return {
        "include_regional": _bool(settings.get("include_regional"), True),
        "include_local": _bool(settings.get("include_local"), True),
    }


def _validate_school(settings: dict) -> dict:
    system = settings.get("system")
    if not isinstance(system, str) or not system:
        raise serializers.ValidationError({"system": "Choose a school system."})
    from apps.scheduling.sources.au_school import SCHOOL_SYSTEMS
    if system not in SCHOOL_SYSTEMS:
        raise serializers.ValidationError({"system": "That school system is not supported yet."})
    return {
        "system": system,
        "show_terms": _bool(settings.get("show_terms"), True),
        "show_holidays": _bool(settings.get("show_holidays"), True),
        "show_student_free": _bool(settings.get("show_student_free"), False),
    }


def _validate_feed(settings: dict) -> dict:
    # Nothing configurable yet beyond the URL, which lives in its own validated column.
    return {}


# --- registry ------------------------------------------------------------------------------

PROVIDERS = {
    ("holidays", "au_holidays"): {
        "label": "Australian public holidays",
        "validate": _validate_holidays,
        "needs_url": False,
        "syncs": True,
        "category": "holiday",
        "colour": "#C2703D",
        "default_show_in_upcoming": True,
    },
    ("school", "au_school_terms"): {
        "label": "Australian school calendar",
        "validate": _validate_school,
        "needs_url": False,
        "syncs": True,
        "category": "school",
        "colour": "#4B7BA8",
        "default_show_in_upcoming": True,
    },
    ("subscription", "ics"): {
        "label": "Subscribed calendar",
        "validate": _validate_feed,
        "needs_url": True,
        "syncs": True,
        "category": "subscription",
        "colour": "#6F5AA8",
        "default_show_in_upcoming": True,
    },
    ("import", "ics"): {
        "label": "Imported calendar file",
        "validate": _validate_feed,
        "needs_url": False,
        # A one-time import is read once at creation and never refreshed from a URL.
        "syncs": False,
        "category": "import",
        "colour": "#5A8A6F",
        "default_show_in_upcoming": True,
    },
}


def is_registered(kind: str, provider: str) -> bool:
    return (kind, provider) in PROVIDERS


def spec(kind: str, provider: str) -> dict:
    try:
        return PROVIDERS[(kind, provider)]
    except KeyError as exc:
        raise serializers.ValidationError(
            {"provider": "That calendar source type is not supported."},
        ) from exc


def validate_settings(kind: str, provider: str, settings) -> dict:
    if not isinstance(settings, dict):
        raise serializers.ValidationError({"settings_json": "Expected an object."})
    return spec(kind, provider)["validate"](settings)


def catalogue() -> list[dict]:
    """What the UI may offer, without exposing internal module names."""
    return [
        {
            "kind": kind,
            "provider": provider,
            "label": entry["label"],
            "needs_url": entry["needs_url"],
            "category": entry["category"],
            "colour": entry["colour"],
        }
        for (kind, provider), entry in PROVIDERS.items()
    ]


def provider_for(source: CalendarSource):
    """The callable that produces this source's events."""
    from apps.scheduling.sources import au_holidays, au_school, feeds

    key = (source.kind, source.provider)
    if key == ("holidays", "au_holidays"):
        return au_holidays.build_events
    if key == ("school", "au_school_terms"):
        return au_school.build_events
    if key in (("subscription", "ics"), ("import", "ics")):
        return feeds.build_events
    raise serializers.ValidationError({"provider": "That calendar source type is not supported."})
