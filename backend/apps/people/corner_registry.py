"""Registration boundary for node-owned Corner projections."""
from __future__ import annotations

from collections.abc import Callable

Provider = Callable[..., dict[str, list[dict]]]
_providers: dict[str, Provider] = {}


def register(node_key: str, provider: Provider) -> None:
    _providers[node_key] = provider


def providers() -> dict[str, Provider]:
    return dict(_providers)
