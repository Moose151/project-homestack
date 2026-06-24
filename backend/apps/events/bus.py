"""Thin event bus wrapping Django signals (D4, Architecture §5).

Nodes publish domain events here; handlers respond without importing the publisher's
models — decoupling nodes from each other while keeping everything in-process.

Each event type gets a Django Signal created on first use. Handlers registered with
`subscribe()` receive `(sender=None, *, payload: dict, **kwargs)`.
"""
from __future__ import annotations

from django.dispatch import Signal

_registry: dict[str, Signal] = {}


def _get_signal(event_type: str) -> Signal:
    if event_type not in _registry:
        _registry[event_type] = Signal()
    return _registry[event_type]


def publish(event_type: str, *, payload: dict) -> None:
    """Send event_type to all registered handlers. No-ops if nobody is subscribed."""
    sig = _registry.get(event_type)
    if sig is not None:
        sig.send(sender=None, payload=payload)


def subscribe(event_type: str, handler) -> None:
    """Register handler to receive events of the given type.

    handler signature: def handler(sender, *, payload: dict, **kwargs) -> None
    weak=False ensures the handler is not garbage-collected.
    """
    _get_signal(event_type).connect(handler, weak=False)
