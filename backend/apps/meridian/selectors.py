"""meridian selectors — read-only queries (Coding Standards §6, D9).

Search uses icontains for SQLite compatibility in tests; production runs on Postgres
where this can be upgraded to SearchVector/tsvector without changing signatures (D9).
"""
from __future__ import annotations

from django.db.models import Q, Sum

from apps.meridian.models import (
    MeridianCategory,
    MeridianGroupGoal,
    MeridianPointsEntry,
    MeridianReward,
    MeridianRewardRequest,
    MeridianRoutine,
    MeridianTask,
    MeridianWishlistItem,
    MeridianWishlistRequest,
)
from apps.people.models import Person
from apps.permissions.visibility import apply_visibility


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

def list_tasks(
    user=None, *, status: str | None = None, assigned_to_person_id: int | None = None,
    hot_only: bool = False, include_archived: bool = False, active_only: bool = False,
) -> list[MeridianTask]:
    qs = MeridianTask.objects.all()
    if not include_archived:
        qs = qs.filter(is_archived=False)
    if active_only:
        qs = qs.filter(is_active=True)
    if status:
        qs = qs.filter(status=status)
    if assigned_to_person_id is not None:
        qs = qs.filter(assigned_to_person_id=assigned_to_person_id)
    if hot_only:
        qs = qs.filter(is_hot=True)
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_task(pk: int) -> MeridianTask | None:
    return MeridianTask.objects.filter(pk=pk).first()


def list_pending_tasks(user=None) -> list[MeridianTask]:
    """Tasks awaiting approval — drives the 'pending approvals' hub widget."""
    return list_tasks(user, status=MeridianTask.Status.PENDING)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

def list_categories() -> list[MeridianCategory]:
    return list(MeridianCategory.objects.order_by("position", "name"))


def get_category(pk: int) -> MeridianCategory | None:
    return MeridianCategory.objects.filter(pk=pk).first()


# ---------------------------------------------------------------------------
# Routines
# ---------------------------------------------------------------------------

def list_routines(
    user=None, *, person_id: int | None = None, active_only: bool = False,
) -> list[MeridianRoutine]:
    """Routines visible to a person.

    A routine assigned to someone is hidden from others; unassigned routines are shown to all.
    When ``person_id`` is given, each routine is annotated with that person's ``streak`` and
    ``done_today`` (read by the serializer).
    """
    qs = MeridianRoutine.objects.all()
    if active_only:
        qs = qs.filter(is_active=True)
    if person_id is not None:
        qs = qs.filter(Q(assigned_to_person_id=person_id) | Q(assigned_to_person__isnull=True))
    if user is not None:
        qs = apply_visibility(qs, user)
    routines = list(qs)
    if person_id is not None:
        from apps.meridian import services
        for r in routines:
            r.streak = services.current_streak(r, person_id)
            r.done_today = services.completed_today(r, person_id)
    return routines


def get_routine(pk: int) -> MeridianRoutine | None:
    return MeridianRoutine.objects.filter(pk=pk).first()


# ---------------------------------------------------------------------------
# Rewards
# ---------------------------------------------------------------------------

def list_rewards(*, active_only: bool = False, include_archived: bool = False,
                 hide_out_of_stock: bool = False) -> list[MeridianReward]:
    qs = MeridianReward.objects.all()
    if not include_archived:
        qs = qs.filter(is_archived=False)
    if active_only:
        qs = qs.filter(is_active=True)
    rewards = list(qs)
    if hide_out_of_stock:
        # Hide sold-out rewards that are configured to disappear (shopper view only).
        rewards = [
            r for r in rewards
            if not (r.disappear_when_empty and r.remaining_stock() == 0)
        ]
    return rewards


def get_reward(pk: int) -> MeridianReward | None:
    return MeridianReward.objects.filter(pk=pk).first()


def list_reward_requests(*, status: str | None = None, person_id: int | None = None) -> list[MeridianRewardRequest]:
    qs = MeridianRewardRequest.objects.select_related("reward")
    if status:
        qs = qs.filter(status=status)
    if person_id is not None:
        qs = qs.filter(requested_by_person_id=person_id)
    return list(qs)


def get_reward_request(pk: int) -> MeridianRewardRequest | None:
    return MeridianRewardRequest.objects.filter(pk=pk).first()


# ---------------------------------------------------------------------------
# Group goals
# ---------------------------------------------------------------------------

def list_goals(*, active_only: bool = False) -> list[MeridianGroupGoal]:
    qs = MeridianGroupGoal.objects.all()
    if active_only:
        qs = qs.filter(is_active=True).exclude(status=MeridianGroupGoal.Status.ARCHIVED)
    return list(qs)


def get_goal(pk: int) -> MeridianGroupGoal | None:
    return MeridianGroupGoal.objects.filter(pk=pk).first()


# ---------------------------------------------------------------------------
# Wishlist
# ---------------------------------------------------------------------------

def list_wishlist_items(*, person_id: int | None = None, active_only: bool = False) -> list[MeridianWishlistItem]:
    qs = MeridianWishlistItem.objects.all()
    if person_id is not None:
        qs = qs.filter(person_id=person_id)
    if active_only:
        qs = qs.filter(is_active=True)
    return list(qs)


def get_wishlist_item(pk: int) -> MeridianWishlistItem | None:
    return MeridianWishlistItem.objects.filter(pk=pk).first()


def list_wishlist_requests(*, status: str | None = None, person_id: int | None = None) -> list[MeridianWishlistRequest]:
    qs = MeridianWishlistRequest.objects.all()
    if status:
        qs = qs.filter(status=status)
    if person_id is not None:
        qs = qs.filter(person_id=person_id)
    return list(qs)


def get_wishlist_request(pk: int) -> MeridianWishlistRequest | None:
    return MeridianWishlistRequest.objects.filter(pk=pk).first()


# ---------------------------------------------------------------------------
# Points
# ---------------------------------------------------------------------------

def points_summary() -> list[dict]:
    """Per-person points balance across the household.

    Returns one row per person that has a points ledger entry, summed.
    """
    rows = (
        MeridianPointsEntry.objects.values("person_id")
        .annotate(balance=Sum("points"))
        .order_by("-balance")
    )
    names = dict(Person.objects.values_list("id", "display_name"))
    return [
        {
            "person_id": r["person_id"],
            "display_name": names.get(r["person_id"], ""),
            "balance": r["balance"] or 0,
        }
        for r in rows
    ]


def list_points_entries(*, person_id: int | None = None, limit: int = 50) -> list[MeridianPointsEntry]:
    qs = MeridianPointsEntry.objects.all()
    if person_id is not None:
        qs = qs.filter(person_id=person_id)
    return list(qs[:limit])


# ---------------------------------------------------------------------------
# Search (D9, Node Spec 12)
# ---------------------------------------------------------------------------

def search_meridian(user, query: str) -> dict:
    """Permission-aware FTS over task names, reward names and categories."""
    tasks = MeridianTask.objects.filter(
        Q(title__icontains=query) | Q(description__icontains=query)
    )
    if user is not None:
        tasks = apply_visibility(tasks, user)
    return {
        "tasks": list(tasks),
        "rewards": list(MeridianReward.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )),
        "categories": list(MeridianCategory.objects.filter(Q(name__icontains=query))),
    }
