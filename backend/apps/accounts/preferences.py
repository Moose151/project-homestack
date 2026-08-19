"""The registry of per-user UI preferences, and the validation that keeps it bounded.

Two rules make this safe to extend:

1. A preference key only exists if it is registered here. An unregistered key is rejected, so
   the table cannot become a general-purpose client-controlled store.
2. Every key declares a validator that returns the *normalised* value actually stored. The
   validator caps sizes and shapes; it is the only writer of this table's contents.

What this deliberately does **not** do is decide what a user may see. Saved values are ordering
hints. A tab key the user has no permission for, or a node that has since been disabled, is
filtered out when the preference is applied — never trusted because it was once saved.
"""
from __future__ import annotations

import re

from rest_framework import serializers

TAB_ORDER = "tab_order"
MOBILE_NAV = "mobile_nav"

# Conservative caps. These are ordering hints for a household app, not a data store: the
# largest real page has well under 20 tabs, and the dock has exactly two slots.
_MAX_PAGES = 40
_MAX_TABS_PER_PAGE = 40
_MOBILE_NAV_SLOTS = 2

# Page and tab identifiers are internal slugs, never free text.
_SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")


def _slug_list(raw, *, field: str, limit: int) -> list[str]:
    if not isinstance(raw, list):
        raise serializers.ValidationError({field: "Expected a list of identifiers."})
    if len(raw) > limit:
        raise serializers.ValidationError({field: f"At most {limit} entries."})
    out: list[str] = []
    for entry in raw:
        if not isinstance(entry, str) or not _SLUG.match(entry):
            raise serializers.ValidationError({field: f"Not a valid identifier: {entry!r}."})
        if entry not in out:  # duplicates carry no meaning in an ordering
            out.append(entry)
    return out


def _validate_tab_order(value) -> dict[str, list[str]]:
    """``{page_key: [tab_key, ...]}`` — one saved ordering per tabbed page.

    A page mapped to an empty list is dropped rather than stored, so "reset this page" needs no
    separate endpoint.
    """
    if not isinstance(value, dict):
        raise serializers.ValidationError({TAB_ORDER: "Expected an object of page orders."})
    if len(value) > _MAX_PAGES:
        raise serializers.ValidationError({TAB_ORDER: f"At most {_MAX_PAGES} pages."})
    out: dict[str, list[str]] = {}
    for page, tabs in value.items():
        if not isinstance(page, str) or not _SLUG.match(page):
            raise serializers.ValidationError({TAB_ORDER: f"Not a valid page key: {page!r}."})
        if tabs is None:
            continue
        ordered = _slug_list(tabs, field=TAB_ORDER, limit=_MAX_TABS_PER_PAGE)
        if ordered:
            out[page] = ordered
    return out


def _validate_mobile_nav(value) -> list[str]:
    """The two configurable bottom-dock slots, as node keys.

    Duplicates are collapsed by ``_slug_list``; the dock repairs any resulting short list from
    its documented priority order, which is also what happens when a saved node is disabled.
    """
    return _slug_list(value, field=MOBILE_NAV, limit=_MOBILE_NAV_SLOTS)


# key -> (validator, default when unset)
REGISTRY = {
    TAB_ORDER: (_validate_tab_order, dict),
    MOBILE_NAV: (_validate_mobile_nav, list),
}


def is_supported(key: str) -> bool:
    return key in REGISTRY


def default_for(key: str):
    return REGISTRY[key][1]()


def validate(key: str, value):
    """Normalise a value for ``key``, or raise ValidationError."""
    if not is_supported(key):
        raise serializers.ValidationError({key: "Unknown preference."})
    return REGISTRY[key][0](value)
