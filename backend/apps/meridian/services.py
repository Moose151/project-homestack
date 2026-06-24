"""meridian services — write operations and the points/approval/reward logic.

This is the proven Meridian behaviour rebuilt natively (Coding Standards §6, D14):
  - tasks move AVAILABLE → PENDING → APPROVED|REJECTED;
  - points are awarded only on approval, recorded per-person in the ledger;
  - rewards are redeemed against the person's balance, deducted on approval.

Calendar entries for dated tasks are maintained ONLY via the scheduling helper (D7).
"""
from __future__ import annotations

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.meridian import events
from apps.meridian.models import (
    MeridianCategory,
    MeridianPointsEntry,
    MeridianReward,
    MeridianRewardRequest,
    MeridianTask,
)
from apps.scheduling.helpers import delete_event_for, sync_event_for


class MeridianError(Exception):
    """Domain error (e.g. insufficient points, illegal state transition)."""


# ---------------------------------------------------------------------------
# Points ledger
# ---------------------------------------------------------------------------

def get_points_balance(person_id: int) -> int:
    agg = MeridianPointsEntry.objects.filter(person_id=person_id).aggregate(total=Sum("points"))
    return agg["total"] or 0


def _record_points(
    acting_user: User, *, person_id: int, points: int, reason: str,
    source_task=None, source_reward_request=None,
) -> MeridianPointsEntry:
    entry = MeridianPointsEntry(
        household=get_active_household(),
        person_id=person_id,
        points=points,
        reason=reason,
        source_task=source_task,
        source_reward_request=source_reward_request,
        created_by=acting_user,
        updated_by=acting_user,
    )
    entry.save()
    events.points_awarded(person_id, entry.household_id, points, reason)
    return entry


def adjust_points(acting_user: User, *, person_id: int, points: int, reason: str = "") -> MeridianPointsEntry:
    """Manual points adjustment by an admin/manager (signed)."""
    return _record_points(acting_user, person_id=person_id, points=points, reason=reason or "Manual adjustment")


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

def create_category(acting_user: User, **data) -> MeridianCategory:
    category = MeridianCategory(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    category.save()
    return category


def update_category(acting_user: User, category: MeridianCategory, **data) -> MeridianCategory:
    allowed = {"name", "colour", "icon", "position"}
    for key, val in data.items():
        if key in allowed:
            setattr(category, key, val)
    category.updated_by = acting_user
    category.save()
    return category


def delete_category(acting_user: User, category: MeridianCategory) -> None:
    category.updated_by = acting_user
    category.save(update_fields=["updated_by", "updated_at"])
    category.soft_delete()


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

def create_task(acting_user: User, **data) -> MeridianTask:
    task = MeridianTask(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    task.save()
    sync_event_for(task)
    events.task_created(task.id, task.household_id)
    return task


def update_task(acting_user: User, task: MeridianTask, **data) -> MeridianTask:
    allowed = {
        "title", "description", "points", "category_id", "assigned_to_person_id",
        "is_hot", "due_at", "recurrence_rule", "visibility",
    }
    for key, val in data.items():
        if key in allowed:
            setattr(task, key, val)
    task.updated_by = acting_user
    task.save()
    sync_event_for(task)
    return task


def delete_task(acting_user: User, task: MeridianTask) -> None:
    delete_event_for(task)
    task.updated_by = acting_user
    task.save(update_fields=["updated_by", "updated_at"])
    task.soft_delete()


def complete_task(acting_user: User, task: MeridianTask, *, person_id: int | None = None) -> MeridianTask:
    """Mark a task done, pending approval. No points awarded until approved.

    ``person_id`` records WHO did the task (a person). Defaults to the task's
    assigned person, or — when a child completes their own task on the kiosk —
    the person linked to the acting user is the natural fallback the caller passes in.
    """
    if task.status in (MeridianTask.Status.PENDING, MeridianTask.Status.APPROVED):
        return task  # already completed/approved — idempotent
    task.status = MeridianTask.Status.PENDING
    task.completed_at = timezone.now()
    task.completed_by_person_id = person_id or task.assigned_to_person_id
    task.approved_at = None
    task.approved_by = None
    task.rejection_reason = ""
    task.updated_by = acting_user
    task.save()
    events.task_completed(task.id, task.household_id, task.completed_by_person_id)
    return task


@transaction.atomic
def approve_task(acting_user: User, task: MeridianTask) -> MeridianTask:
    """Approve a completed task and award its points to the completing person."""
    if task.status != MeridianTask.Status.PENDING:
        raise MeridianError("Only tasks pending approval can be approved.")
    task.status = MeridianTask.Status.APPROVED
    task.approved_at = timezone.now()
    task.approved_by = acting_user
    task.rejection_reason = ""
    task.updated_by = acting_user
    task.save()

    person_id = task.completed_by_person_id or task.assigned_to_person_id
    if person_id and task.points:
        _record_points(
            acting_user, person_id=person_id, points=task.points,
            reason=f"Task approved: {task.title}", source_task=task,
        )
    events.task_approved(task.id, task.household_id, person_id, task.points)
    return task


def reject_task(acting_user: User, task: MeridianTask, *, reason: str = "") -> MeridianTask:
    """Reject a completed task; it returns to AVAILABLE so it can be retried."""
    if task.status != MeridianTask.Status.PENDING:
        raise MeridianError("Only tasks pending approval can be rejected.")
    task.status = MeridianTask.Status.AVAILABLE
    task.completed_at = None
    task.completed_by_person_id = None
    task.approved_at = None
    task.approved_by = None
    task.rejection_reason = reason
    task.updated_by = acting_user
    task.save()
    events.task_rejected(task.id, task.household_id)
    return task


# ---------------------------------------------------------------------------
# Rewards
# ---------------------------------------------------------------------------

def create_reward(acting_user: User, **data) -> MeridianReward:
    reward = MeridianReward(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    reward.save()
    return reward


def update_reward(acting_user: User, reward: MeridianReward, **data) -> MeridianReward:
    allowed = {"name", "description", "cost_points", "icon", "colour", "is_active"}
    for key, val in data.items():
        if key in allowed:
            setattr(reward, key, val)
    reward.updated_by = acting_user
    reward.save()
    return reward


def delete_reward(acting_user: User, reward: MeridianReward) -> None:
    reward.updated_by = acting_user
    reward.save(update_fields=["updated_by", "updated_at"])
    reward.soft_delete()


def request_reward(acting_user: User, reward: MeridianReward, *, person_id: int) -> MeridianRewardRequest:
    """A person requests to redeem a reward. Balance is verified now and again on approval."""
    if not reward.is_active:
        raise MeridianError("This reward is not available.")
    if get_points_balance(person_id) < reward.cost_points:
        raise MeridianError("Not enough points for this reward.")
    req = MeridianRewardRequest(
        household=get_active_household(),
        reward=reward,
        requested_by_person_id=person_id,
        status=MeridianRewardRequest.Status.PENDING,
        created_by=acting_user,
        updated_by=acting_user,
    )
    req.save()
    events.reward_requested(req.id, req.household_id, person_id)
    return req


@transaction.atomic
def approve_reward_request(acting_user: User, req: MeridianRewardRequest) -> MeridianRewardRequest:
    """Approve a reward request, deducting its cost from the person's balance."""
    if req.status != MeridianRewardRequest.Status.PENDING:
        raise MeridianError("Only pending reward requests can be approved.")
    cost = req.reward.cost_points
    if get_points_balance(req.requested_by_person_id) < cost:
        raise MeridianError("Not enough points to fulfil this reward.")
    req.status = MeridianRewardRequest.Status.APPROVED
    req.points_spent = cost
    req.approved_at = timezone.now()
    req.approved_by = acting_user
    req.updated_by = acting_user
    req.save()
    if cost:
        _record_points(
            acting_user, person_id=req.requested_by_person_id, points=-cost,
            reason=f"Reward redeemed: {req.reward.name}", source_reward_request=req,
        )
    events.reward_approved(req.id, req.household_id, req.requested_by_person_id, cost)
    return req


def reject_reward_request(acting_user: User, req: MeridianRewardRequest, *, reason: str = "") -> MeridianRewardRequest:
    if req.status != MeridianRewardRequest.Status.PENDING:
        raise MeridianError("Only pending reward requests can be rejected.")
    req.status = MeridianRewardRequest.Status.REJECTED
    req.rejection_reason = reason
    req.updated_by = acting_user
    req.save()
    return req
