"""Event-bus handlers (D4/D20).

This is the cross-node seam: achievements reacts to other nodes' domain events and awards
badges, **without importing those nodes' models**. Count-based criteria use the app's own
per-person counters; metric criteria (e.g. routine streaks) read the value carried on the event.

Adding a new producer node later is purely additive: seed its badges and subscribe here — no
changes to the producing node beyond the events it already publishes.
"""
from __future__ import annotations

from apps.achievements import services
from apps.events.bus import subscribe

# event_type → (counter_key, [(threshold, badge_code), …]) — each event increments the counter.
_COUNT_RULES: dict[str, tuple[str, list[tuple[int, str]]]] = {
    "meridian.task_approved": (
        "meridian.tasks_approved",
        [(1, "first_task"), (5, "five_tasks"), (10, "ten_tasks")],
    ),
    "meridian.routine_completed": (
        "meridian.routines_completed",
        [(10, "routine_10"), (50, "routine_50"), (100, "routine_100")],
    ),
    "meridian.goal_contributed": (
        "meridian.goal_contributions",
        [(1, "group_contributor")],
    ),
    "meridian.wishlist_contributed": (
        "meridian.wishlist_contributions",
        [(1, "wishlist_saver")],
    ),
}

_STREAK_BADGES = [(3, "routine_streak_3"), (7, "routine_streak_7"),
                  (28, "routine_streak_28"), (30, "routine_streak_30")]

# Transaction types that count toward the lifetime "total earned" milestone (mirrors Meridian).
_EARNING_TYPES = {"task_approved", "routine_completed", "allowance", "manual_adjustment"}


def _award_thresholds(person_id: int, value: int, thresholds: list[tuple[int, str]]) -> None:
    for threshold, code in thresholds:
        if value >= threshold:
            services.award_badge(person_id, code)


def _make_count_handler(counter_key: str, thresholds: list[tuple[int, str]]):
    def handler(sender, *, payload: dict, **kwargs) -> None:
        person_id = payload.get("person_id")
        if not person_id:
            return
        value = services.bump_counter(person_id, counter_key)
        _award_thresholds(person_id, value, thresholds)
    return handler


def _on_routine_streak(sender, *, payload: dict, **kwargs) -> None:
    person_id = payload.get("person_id")
    streak = payload.get("streak") or 0
    if not person_id:
        return
    value = services.raise_counter_to(person_id, "meridian.routine_streak_max", streak)
    _award_thresholds(person_id, value, _STREAK_BADGES)


def _on_points_awarded(sender, *, payload: dict, **kwargs) -> None:
    person_id = payload.get("person_id")
    points = payload.get("points") or 0
    if not person_id or points <= 0 or payload.get("transaction_type") not in _EARNING_TYPES:
        return
    value = services.bump_counter(person_id, "meridian.total_earned", points)
    _award_thresholds(person_id, value, [(100, "hundred_points_earned")])


def _on_wishlist_funded(sender, *, payload: dict, **kwargs) -> None:
    person_id = payload.get("person_id")
    if person_id:
        services.award_badge(person_id, "wishlist_funded")


def _on_routine_perfect_month(sender, *, payload: dict, **kwargs) -> None:
    person_id = payload.get("person_id")
    if person_id:
        services.award_badge(person_id, "routine_perfect_month")


def connect() -> None:
    """Wire all handlers to the bus. Called once from AppConfig.ready()."""
    for event_type, (counter_key, thresholds) in _COUNT_RULES.items():
        subscribe(event_type, _make_count_handler(counter_key, thresholds))
    subscribe("meridian.routine_completed", _on_routine_streak)
    subscribe("meridian.points_awarded", _on_points_awarded)
    subscribe("meridian.wishlist_funded", _on_wishlist_funded)
    subscribe("meridian.routine_perfect_month", _on_routine_perfect_month)
