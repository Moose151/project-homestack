"""meridian selectors — read-only queries (Coding Standards §6, D9).

Search uses icontains for SQLite compatibility in tests; production runs on Postgres
where this can be upgraded to SearchVector/tsvector without changing signatures (D9).
"""
from __future__ import annotations

from django.db.models import Q, Sum

from apps.meridian.models import (
    MeridianCategory,
    MeridianPointsEntry,
    MeridianReward,
    MeridianRewardRequest,
    MeridianTask,
)
from apps.people.models import Person
from apps.permissions.visibility import apply_visibility


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

def list_tasks(
    user=None, *, status: str | None = None, assigned_to_person_id: int | None = None,
    hot_only: bool = False,
) -> list[MeridianTask]:
    qs = MeridianTask.objects.all()
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
# Rewards
# ---------------------------------------------------------------------------

def list_rewards(*, active_only: bool = False) -> list[MeridianReward]:
    qs = MeridianReward.objects.all()
    if active_only:
        qs = qs.filter(is_active=True)
    return list(qs)


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
