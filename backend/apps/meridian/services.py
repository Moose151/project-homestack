"""meridian services — write operations and the points/approval/reward logic.

This is the proven Meridian behaviour rebuilt natively (Coding Standards §6, D14):
  - tasks move AVAILABLE → PENDING → APPROVED|REJECTED;
  - points are awarded only on approval, recorded per-person in the ledger;
  - rewards are redeemed against the person's balance, deducted on approval.

Calendar entries for dated tasks are maintained ONLY via the scheduling helper (D7).
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.meridian import events
from apps.notifications import services as notifications
from apps.meridian.models import (
    MeridianAllowance,
    MeridianCategory,
    MeridianGroupGoal,
    MeridianGroupGoalContribution,
    MeridianPointsEntry,
    MeridianReward,
    MeridianRewardRequest,
    MeridianRoutine,
    MeridianRoutineCompletion,
    MeridianTask,
    MeridianTaskCompletion,
    MeridianWishlistContribution,
    MeridianWishlistItem,
    MeridianWishlistRequest,
)
from apps.scheduling.helpers import delete_event_for, sync_event_for


class MeridianError(Exception):
    """Domain error (e.g. insufficient points, illegal state transition)."""


# ---------------------------------------------------------------------------
# Points ledger
# ---------------------------------------------------------------------------

_TxType = MeridianPointsEntry.TransactionType


def get_points_balance(person_id: int) -> int:
    """Current spendable balance — the sum of every ledger entry for the person."""
    agg = MeridianPointsEntry.objects.filter(person_id=person_id).aggregate(total=Sum("points"))
    return agg["total"] or 0


def get_total_earned(person_id: int) -> int:
    """Lifetime points earned — positive *earning* entries only (legacy parity).

    Spending, reservations, refunds and contributions never reduce this figure; it is used
    for earning-milestone badges and reports.
    """
    agg = (
        MeridianPointsEntry.objects.filter(
            person_id=person_id,
            transaction_type__in=MeridianPointsEntry.EARNING_TYPES,
            points__gt=0,
        )
        .aggregate(total=Sum("points"))
    )
    return agg["total"] or 0


def _record_points(
    acting_user: User | None, *, person_id: int, points: int, reason: str,
    transaction_type: str = _TxType.MANUAL_ADJUSTMENT,
    source_task=None, source_reward_request=None, source_routine=None,
) -> MeridianPointsEntry:
    entry = MeridianPointsEntry(
        household=get_active_household(),
        person_id=person_id,
        points=points,
        transaction_type=transaction_type,
        reason=reason,
        source_task=source_task,
        source_reward_request=source_reward_request,
        source_routine=source_routine,
        created_by=acting_user,
        updated_by=acting_user,
    )
    entry.save()
    events.points_awarded(person_id, entry.household_id, points, reason, transaction_type)
    return entry


def adjust_points(acting_user: User, *, person_id: int, points: int, reason: str = "") -> MeridianPointsEntry:
    """Manual points adjustment by an admin/manager (signed)."""
    return _record_points(
        acting_user, person_id=person_id, points=points,
        reason=reason or "Manual adjustment",
        transaction_type=_TxType.MANUAL_ADJUSTMENT,
    )


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
    allowed = {"name", "kind", "colour", "icon", "position"}
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
        "is_hot", "hot_bonus_points", "hot_label", "due_at", "recurrence_rule", "visibility",
        "completion_behavior", "completion_scope", "availability_window",
        "is_active", "is_archived",
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


def _task_cycle_start(task: MeridianTask, *, now=None):
    """Return the lower bound for active completions in the current recurrence cycle.

    Native Meridian's weekly recurrence ignores completions older than the current week. HomeStack
    stores recurrence as an RRULE string, but the current UI only needs the same weekly re-arm
    behaviour: any non-empty recurrence rule gets a Monday-start weekly cycle.
    """
    if not task.recurrence_rule:
        return None
    now = now or timezone.now()
    local_day = timezone.localtime(now).date()
    return timezone.make_aware(
        datetime.combine(local_day - timedelta(days=local_day.weekday()), time.min)
    )


def _active_task_completions(task: MeridianTask):
    qs = MeridianTaskCompletion.objects.filter(
        task=task,
        status__in=[
            MeridianTaskCompletion.Status.SUBMITTED,
            MeridianTaskCompletion.Status.APPROVED,
        ],
    )
    cycle_start = _task_cycle_start(task)
    if cycle_start is not None:
        qs = qs.filter(submitted_at__gte=cycle_start)
    return qs


def _sync_task_from_latest_completion(task: MeridianTask) -> MeridianTask:
    latest = task.completions.order_by("-submitted_at", "-id").first()
    if latest is None:
        task.status = MeridianTask.Status.AVAILABLE
        task.completed_at = None
        task.completed_by_person_id = None
        task.approved_at = None
        task.approved_by = None
        task.rejection_reason = ""
    elif latest.status == MeridianTaskCompletion.Status.SUBMITTED:
        task.status = MeridianTask.Status.PENDING
        task.completed_at = latest.submitted_at
        task.completed_by_person_id = latest.person_id
        task.approved_at = None
        task.approved_by = None
        task.rejection_reason = ""
    elif latest.status == MeridianTaskCompletion.Status.APPROVED:
        task.status = MeridianTask.Status.APPROVED
        task.completed_at = latest.submitted_at
        task.completed_by_person_id = latest.person_id
        task.approved_at = latest.reviewed_at
        task.approved_by = latest.reviewed_by
        task.rejection_reason = ""
    else:
        task.status = MeridianTask.Status.AVAILABLE
        task.completed_at = None
        task.completed_by_person_id = None
        task.approved_at = latest.reviewed_at
        task.approved_by = latest.reviewed_by
        task.rejection_reason = latest.rejection_reason
    task.save(update_fields=[
        "status", "completed_at", "completed_by_person", "approved_at", "approved_by",
        "rejection_reason", "updated_at",
    ])
    return task


def submit_task_completion(
    acting_user: User,
    task: MeridianTask,
    *,
    person_id: int | None = None,
    evidence_photo: str = "",
) -> MeridianTaskCompletion:
    """Submit a task completion for review. No points are awarded until approval.

    ``person_id`` records WHO did the task (a person). Defaults to the task's
    assigned person, or — when a child completes their own task on the kiosk —
    the person linked to the acting user is the natural fallback the caller passes in.
    """
    if not task.is_active or task.is_archived:
        raise MeridianError("This task is not active.")
    person_id = person_id or task.assigned_to_person_id
    if person_id is None:
        raise MeridianError("No person to complete on behalf of.")

    active = _active_task_completions(task)
    if task.completion_scope == MeridianTask.CompletionScope.HOUSEHOLD:
        existing = active.order_by("-submitted_at", "-id").first()
    else:
        existing = active.filter(person_id=person_id).order_by("-submitted_at", "-id").first()
    if existing:
        return existing

    completion = MeridianTaskCompletion(
        household=get_active_household(),
        task=task,
        person_id=person_id,
        evidence_photo=evidence_photo,
        created_by=acting_user,
        updated_by=acting_user,
    )
    completion.save()
    task.updated_by = acting_user
    task.save(update_fields=["updated_by", "updated_at"])
    _sync_task_from_latest_completion(task)
    events.task_completed(task.id, task.household_id, person_id)
    return completion


def complete_task(acting_user: User, task: MeridianTask, *, person_id: int | None = None) -> MeridianTask:
    """Backward-compatible task-level completion API."""
    submit_task_completion(acting_user, task, person_id=person_id)
    task.refresh_from_db()
    return task


@transaction.atomic
def approve_task_completion(
    acting_user: User, completion: MeridianTaskCompletion, *, review_note: str = ""
) -> MeridianTaskCompletion:
    """Approve a submitted completion and award task points to its person."""
    if completion.status != MeridianTaskCompletion.Status.SUBMITTED:
        raise MeridianError("Only submitted completions can be approved.")
    task = completion.task
    completion.status = MeridianTaskCompletion.Status.APPROVED
    completion.reviewed_at = timezone.now()
    completion.reviewed_by = acting_user
    completion.rejection_reason = ""
    completion.review_note = review_note
    completion.updated_by = acting_user
    completion.save()

    # One-off tasks are hidden once approved; repeatable tasks stay active (legacy parity).
    if task.completion_behavior == MeridianTask.CompletionBehavior.HIDE_AFTER_APPROVAL:
        task.is_active = False
    task.updated_by = acting_user
    task.save()

    _sync_task_from_latest_completion(task)
    person_id = completion.person_id
    awarded = task.award_value
    if person_id and awarded:
        _record_points(
            acting_user, person_id=person_id, points=awarded,
            reason=f"Task approved: {task.title}", source_task=task,
            transaction_type=_TxType.TASK_APPROVED,
        )
    notifications.notify_person_id(
        person_id, title="Task approved",
        message=f"'{task.title}' was approved — you earned {awarded} points.",
        level=notifications.Notification.Level.SUCCESS, source_node="meridian",
    )
    events.task_approved(task.id, task.household_id, person_id, awarded)
    return completion


@transaction.atomic
def approve_task(acting_user: User, task: MeridianTask) -> MeridianTask:
    """Backward-compatible task-level approval: approve the latest submitted completion."""
    completion = task.completions.filter(
        status=MeridianTaskCompletion.Status.SUBMITTED
    ).order_by("-submitted_at", "-id").first()
    if completion is None:
        raise MeridianError("Only tasks pending approval can be approved.")
    approve_task_completion(acting_user, completion)
    task.refresh_from_db()
    return task


def reject_task_completion(
    acting_user: User,
    completion: MeridianTaskCompletion,
    *,
    reason: str = "",
    review_note: str = "",
) -> MeridianTaskCompletion:
    """Reject a submitted completion; the task can be retried."""
    if completion.status != MeridianTaskCompletion.Status.SUBMITTED:
        raise MeridianError("Only submitted completions can be rejected.")
    task = completion.task
    notifications.notify_person_id(
        completion.person_id, title="Task not approved",
        message=f"'{task.title}' was sent back" + (f": {reason}" if reason else "."),
        level=notifications.Notification.Level.WARNING, source_node="meridian",
    )
    completion.status = MeridianTaskCompletion.Status.REJECTED
    completion.reviewed_at = timezone.now()
    completion.reviewed_by = acting_user
    completion.rejection_reason = reason
    completion.review_note = review_note
    completion.updated_by = acting_user
    completion.save()
    task.updated_by = acting_user
    task.save(update_fields=["updated_by", "updated_at"])
    _sync_task_from_latest_completion(task)
    events.task_rejected(task.id, task.household_id)
    return completion


def reject_task(acting_user: User, task: MeridianTask, *, reason: str = "") -> MeridianTask:
    """Backward-compatible task-level rejection: reject the latest submitted completion."""
    completion = task.completions.filter(
        status=MeridianTaskCompletion.Status.SUBMITTED
    ).order_by("-submitted_at", "-id").first()
    if completion is None:
        raise MeridianError("Only tasks pending approval can be rejected.")
    reject_task_completion(acting_user, completion, reason=reason)
    task.refresh_from_db()
    return task


# ---------------------------------------------------------------------------
# Routines + streaks
# ---------------------------------------------------------------------------

def create_routine(acting_user: User, **data) -> MeridianRoutine:
    routine = MeridianRoutine(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    routine.save()
    return routine


def update_routine(acting_user: User, routine: MeridianRoutine, **data) -> MeridianRoutine:
    allowed = {"title", "description", "points", "assigned_to_person_id", "is_active", "visibility"}
    for key, val in data.items():
        if key in allowed:
            setattr(routine, key, val)
    routine.updated_by = acting_user
    routine.save()
    return routine


def delete_routine(acting_user: User, routine: MeridianRoutine) -> None:
    routine.updated_by = acting_user
    routine.save(update_fields=["updated_by", "updated_at"])
    routine.soft_delete()


def completed_today(routine: MeridianRoutine, person_id: int, *, on: date | None = None) -> bool:
    day = on or timezone.localdate()
    return MeridianRoutineCompletion.objects.filter(
        routine=routine, person_id=person_id, completed_date=day, voided=False
    ).exists()


def current_streak(routine: MeridianRoutine, person_id: int, *, auto_end: bool | None = None) -> int:
    """Consecutive-day streak for a person on a routine (legacy parity).

    With ``auto_end=False`` the streak is the total count of distinct completion days and never
    resets automatically (split-household mode); otherwise a gap of more than one day breaks it.
    When ``auto_end`` is None it falls back to the household ``auto_end_streaks`` setting
    (default False — streaks don't auto-break, matching the legacy default).
    """
    if auto_end is None:
        from apps.meridian import config
        auto_end = bool(config.get_setting("auto_end_streaks"))
    dates = sorted(
        {
            c.completed_date
            for c in MeridianRoutineCompletion.objects.filter(
                routine=routine, person_id=person_id, voided=False
            )
        },
        reverse=True,
    )
    if not dates:
        return 0
    if not auto_end:
        return len(dates)
    today = timezone.localdate()
    if dates[0] < today - timedelta(days=1):
        return 0
    streak = 1
    for i in range(1, len(dates)):
        if dates[i] == dates[i - 1] - timedelta(days=1):
            streak += 1
        else:
            break
    return streak


@transaction.atomic
def complete_routine(acting_user: User, routine: MeridianRoutine, *, person_id: int) -> MeridianRoutineCompletion:
    """Record a routine completion for today and award its points immediately (no approval).

    Idempotent per person/day: completing an already-done routine today is a no-op that returns
    the existing completion without awarding points again.
    """
    if not routine.is_active:
        raise MeridianError("This routine is not active.")
    today = timezone.localdate()
    existing = MeridianRoutineCompletion.objects.filter(
        routine=routine, person_id=person_id, completed_date=today, voided=False
    ).first()
    if existing:
        return existing
    completion = MeridianRoutineCompletion(
        household=get_active_household(),
        routine=routine,
        person_id=person_id,
        completed_date=today,
        created_by=acting_user,
        updated_by=acting_user,
    )
    completion.save()
    if routine.points:
        _record_points(
            acting_user, person_id=person_id, points=routine.points,
            reason=f"Routine completed: {routine.title}", source_routine=routine,
            transaction_type=_TxType.ROUTINE_COMPLETED,
        )
    events.routine_completed(
        routine.id, routine.household_id, person_id, current_streak(routine, person_id)
    )
    return completion


@transaction.atomic
def void_routine_completion(acting_user: User, completion: MeridianRoutineCompletion) -> MeridianRoutineCompletion:
    """Admin voids a completion (streak reset / rejection) and claws back its points."""
    if completion.voided:
        return completion
    completion.voided = True
    completion.updated_by = acting_user
    completion.save(update_fields=["voided", "updated_by", "updated_at"])
    if completion.routine and completion.routine.points:
        _record_points(
            acting_user, person_id=completion.person_id, points=-completion.routine.points,
            reason=f"Routine completion voided: {completion.routine.title}",
            source_routine=completion.routine, transaction_type=_TxType.MANUAL_ADJUSTMENT,
        )
    return completion


# ---------------------------------------------------------------------------
# Scheduled work (D5 — run by a management command on cron, not a live scheduler)
# ---------------------------------------------------------------------------

def award_allowances(*, on: date | None = None) -> int:
    """Award the weekly allowance to every eligible person whose configured weekday is ``on``.

    Idempotent for the day: a person who already has an allowance entry dated ``on`` is skipped,
    so re-running the command on the same day does not double-pay.
    """
    day = on or timezone.localdate()
    weekday = day.weekday()
    awarded = 0
    allowances = MeridianAllowance.objects.filter(
        is_active=True, amount__gt=0, weekday=weekday
    ).select_related("person")
    reason = f"Weekly allowance ({day.isoformat()})"
    for allowance in allowances:
        # Idempotent for the day: keyed on the allowance date in the reason, so re-running the
        # command (or running it with an explicit --date) never double-pays.
        already = MeridianPointsEntry.objects.filter(
            person_id=allowance.person_id,
            transaction_type=_TxType.ALLOWANCE,
            reason=reason,
        ).exists()
        if already:
            continue
        _record_points(
            None, person_id=allowance.person_id, points=allowance.amount,
            reason=reason, transaction_type=_TxType.ALLOWANCE,
        )
        notifications.notify_person_id(
            allowance.person_id, title="Allowance",
            message=f"You received your weekly allowance of {allowance.amount} points.",
            level=notifications.Notification.Level.SUCCESS, source_node="meridian",
        )
        awarded += 1
    return awarded


def set_allowance_config(acting_user: User, rows: list[dict]) -> None:
    """Upsert per-person weekly allowance settings from the admin cockpit."""
    for row in rows:
        person_id = row.get("person_id")
        if person_id is None:
            continue
        amount = max(0, int(row.get("amount") or 0))
        weekday = int(row.get("weekday") or 0)
        if weekday < 0 or weekday > 6:
            raise MeridianError("Allowance weekday must be between 0 and 6.")
        is_active = bool(row.get("is_active")) and amount > 0
        allowance, _ = MeridianAllowance.objects.get_or_create(
            person_id=person_id,
            defaults={
                "household": get_active_household(),
                "created_by": acting_user,
                "updated_by": acting_user,
            },
        )
        allowance.amount = amount
        allowance.weekday = weekday
        allowance.is_active = is_active
        allowance.updated_by = acting_user
        allowance.save()


def award_perfect_month_badges(*, year: int, month: int) -> int:
    """Emit a perfect-month event for each person who completed a routine on every day of the
    given calendar month. Achievements awards the badge (idempotent) via the bus (D4)."""
    import calendar as _calendar

    days_in_month = _calendar.monthrange(year, month)[1]
    person_days: dict[int, set] = {}
    completions = MeridianRoutineCompletion.objects.filter(
        completed_date__year=year, completed_date__month=month, voided=False
    ).values_list("person_id", "completed_date")
    for person_id, completed_date in completions:
        person_days.setdefault(person_id, set()).add(completed_date.day)
    emitted = 0
    household = get_active_household()
    for person_id, days in person_days.items():
        if len(days) >= days_in_month:
            events.routine_perfect_month(person_id, household.id, year, month)
            emitted += 1
    return emitted


# ---------------------------------------------------------------------------
# Group goals
# ---------------------------------------------------------------------------

def create_goal(acting_user: User, **data) -> MeridianGroupGoal:
    goal = MeridianGroupGoal(
        household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data
    )
    goal.save()
    return goal


def update_goal(acting_user: User, goal: MeridianGroupGoal, **data) -> MeridianGroupGoal:
    allowed = {"title", "description", "target_points", "price_estimate", "store_url",
               "image_url", "status", "is_active"}
    for key, val in data.items():
        if key in allowed:
            setattr(goal, key, val)
    goal.updated_by = acting_user
    goal.save()
    return goal


def delete_goal(acting_user: User, goal: MeridianGroupGoal) -> None:
    goal.updated_by = acting_user
    goal.save(update_fields=["updated_by", "updated_at"])
    goal.soft_delete()


@transaction.atomic
def contribute_to_goal(
    acting_user: User, goal: MeridianGroupGoal, *, person_id: int, amount: int
) -> MeridianGroupGoalContribution:
    """A person contributes points to a group goal; the points are reserved (spent) now and
    refundable later. Marks the goal funded once the target is reached."""
    from apps.meridian import config
    if not config.get_setting("group_goals_enabled"):
        raise MeridianError("Group goals are disabled.")
    if not goal.is_active or goal.status == MeridianGroupGoal.Status.ARCHIVED:
        raise MeridianError("This goal is not accepting contributions.")
    if amount <= 0:
        raise MeridianError("Contribution must be a positive number of points.")
    if get_points_balance(person_id) < amount:
        raise MeridianError("Not enough points to contribute that much.")
    contribution = MeridianGroupGoalContribution(
        household=get_active_household(), goal=goal, person_id=person_id, amount=amount,
        created_by=acting_user, updated_by=acting_user,
    )
    contribution.save()
    _record_points(
        acting_user, person_id=person_id, points=-amount,
        reason=f"Group goal contribution: {goal.title}",
        transaction_type=_TxType.GROUP_GOAL_CONTRIBUTION,
    )
    if goal.is_funded() and goal.status != MeridianGroupGoal.Status.FUNDED:
        goal.status = MeridianGroupGoal.Status.FUNDED
        goal.updated_by = acting_user
        goal.save(update_fields=["status", "updated_by", "updated_at"])
    events.goal_contributed(goal.id, goal.household_id, person_id, amount)
    return contribution


@transaction.atomic
def refund_goal_contribution(
    acting_user: User, contribution: MeridianGroupGoalContribution
) -> MeridianGroupGoalContribution:
    """Refund an active goal contribution (admin, or when a goal is cancelled)."""
    if contribution.status != MeridianGroupGoalContribution.Status.ACTIVE:
        return contribution
    contribution.status = MeridianGroupGoalContribution.Status.REFUNDED
    contribution.updated_by = acting_user
    contribution.save(update_fields=["status", "updated_by", "updated_at"])
    _record_points(
        acting_user, person_id=contribution.person_id, points=contribution.amount,
        reason=f"Group goal contribution refunded: {contribution.goal.title}",
        transaction_type=_TxType.GROUP_GOAL_REFUND,
    )
    return contribution


# ---------------------------------------------------------------------------
# Wishlist
# ---------------------------------------------------------------------------

def request_wishlist_item(
    acting_user: User, *, person_id: int, requested_name: str, requested_description: str = ""
) -> MeridianWishlistRequest:
    """A person asks for an item to be added to their wishlist (awaits admin approval)."""
    from apps.meridian import config
    if not config.get_setting("wishlist_requests_enabled"):
        raise MeridianError("Wishlist requests are disabled.")
    if not requested_name.strip():
        raise MeridianError("A wishlist item needs a name.")
    req = MeridianWishlistRequest(
        household=get_active_household(), person_id=person_id,
        requested_name=requested_name.strip(), requested_description=requested_description,
        created_by=acting_user, updated_by=acting_user,
    )
    req.save()
    return req


@transaction.atomic
def approve_wishlist_request(
    acting_user: User, req: MeridianWishlistRequest, *, point_cost: int, **item_data
) -> MeridianWishlistItem:
    """Admin approves a request into a wishlist item with a point cost the person saves toward."""
    if req.status != MeridianWishlistRequest.Status.REQUESTED:
        raise MeridianError("Only pending wishlist requests can be approved.")
    req.status = MeridianWishlistRequest.Status.APPROVED
    req.reviewed_at = timezone.now()
    req.reviewed_by = acting_user
    req.updated_by = acting_user
    req.save()
    allowed = {"description", "price_estimate", "store_url", "image_url"}
    item = MeridianWishlistItem(
        household=get_active_household(), person_id=req.person_id,
        name=req.requested_name, point_cost=point_cost,
        description=req.requested_description,
        created_by=acting_user, updated_by=acting_user,
        **{k: v for k, v in item_data.items() if k in allowed},
    )
    item.save()
    return item


def reject_wishlist_request(acting_user: User, req: MeridianWishlistRequest, *, reason: str = "") -> MeridianWishlistRequest:
    if req.status != MeridianWishlistRequest.Status.REQUESTED:
        raise MeridianError("Only pending wishlist requests can be rejected.")
    req.status = MeridianWishlistRequest.Status.REJECTED
    req.rejection_reason = reason
    req.reviewed_at = timezone.now()
    req.reviewed_by = acting_user
    req.updated_by = acting_user
    req.save()
    return req


def create_wishlist_item(acting_user: User, *, person_id: int, name: str, point_cost: int, **data) -> MeridianWishlistItem:
    """Admin adds a wishlist item directly (no request step)."""
    allowed = {"description", "price_estimate", "store_url", "image_url"}
    item = MeridianWishlistItem(
        household=get_active_household(), person_id=person_id, name=name, point_cost=point_cost,
        created_by=acting_user, updated_by=acting_user,
        **{k: v for k, v in data.items() if k in allowed},
    )
    item.save()
    return item


def delete_wishlist_item(acting_user: User, item: MeridianWishlistItem) -> None:
    item.updated_by = acting_user
    item.save(update_fields=["updated_by", "updated_at"])
    item.soft_delete()


@transaction.atomic
def contribute_to_wishlist(
    acting_user: User, item: MeridianWishlistItem, *, person_id: int, amount: int
) -> MeridianWishlistContribution:
    """A person saves points toward their wishlist item; points are reserved and refundable."""
    if not item.is_active or item.status == MeridianWishlistItem.Status.FULFILLED:
        raise MeridianError("This wishlist item is not accepting contributions.")
    if amount <= 0:
        raise MeridianError("Contribution must be a positive number of points.")
    if get_points_balance(person_id) < amount:
        raise MeridianError("Not enough points to save that much.")
    contribution = MeridianWishlistContribution(
        household=get_active_household(), item=item, person_id=person_id, amount=amount,
        created_by=acting_user, updated_by=acting_user,
    )
    contribution.save()
    _record_points(
        acting_user, person_id=person_id, points=-amount,
        reason=f"Wishlist saving: {item.name}",
        transaction_type=_TxType.WISHLIST_CONTRIBUTION,
    )
    events.wishlist_contributed(item.id, item.household_id, person_id, amount)
    if item.is_funded() and item.status == MeridianWishlistItem.Status.ACTIVE:
        item.status = MeridianWishlistItem.Status.FUNDED
        item.updated_by = acting_user
        item.save(update_fields=["status", "updated_by", "updated_at"])
        events.wishlist_funded(item.id, item.household_id, person_id)
    return contribution


@transaction.atomic
def refund_wishlist_contribution(
    acting_user: User, contribution: MeridianWishlistContribution
) -> MeridianWishlistContribution:
    if contribution.status != MeridianWishlistContribution.Status.ACTIVE:
        return contribution
    contribution.status = MeridianWishlistContribution.Status.REFUNDED
    contribution.updated_by = acting_user
    contribution.save(update_fields=["status", "updated_by", "updated_at"])
    _record_points(
        acting_user, person_id=contribution.person_id, points=contribution.amount,
        reason=f"Wishlist saving refunded: {contribution.item.name}",
        transaction_type=_TxType.WISHLIST_REFUND,
    )
    return contribution


def fulfill_wishlist_item(acting_user: User, item: MeridianWishlistItem) -> MeridianWishlistItem:
    """Admin marks a funded wishlist item as fulfilled (the real item was bought/given)."""
    item.status = MeridianWishlistItem.Status.FULFILLED
    item.updated_by = acting_user
    item.save(update_fields=["status", "updated_by", "updated_at"])
    return item


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
    allowed = {
        "name", "description", "cost_points", "category_id", "icon", "colour", "image_url",
        "is_active", "is_archived", "price_estimate", "store_url",
        "quantity", "allow_multiple_in_cart", "disappear_when_empty", "daily_limit_per_user",
    }
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


@transaction.atomic
def request_reward(acting_user: User, reward: MeridianReward, *, person_id: int) -> MeridianRewardRequest:
    """A person requests to redeem a reward.

    Points are **reserved** (deducted) immediately (legacy parity, D19): the cost is held as a
    negative ledger entry so it cannot be double-spent on a parallel request. The hold is
    refunded if the request is later rejected or cancelled; approval does not deduct again.
    """
    if not reward.is_active or reward.is_archived:
        raise MeridianError("This reward is not available.")
    remaining = reward.remaining_stock()
    if remaining is not None and remaining <= 0:
        raise MeridianError("This reward is out of stock.")
    daily_left = reward.daily_remaining_for_person(person_id)
    if daily_left is not None and daily_left <= 0:
        raise MeridianError("Daily limit reached for this reward.")
    cost = reward.cost_points
    if get_points_balance(person_id) < cost:
        raise MeridianError("Not enough points for this reward.")
    req = MeridianRewardRequest(
        household=get_active_household(),
        reward=reward,
        requested_by_person_id=person_id,
        status=MeridianRewardRequest.Status.PENDING,
        points_spent=cost,
        created_by=acting_user,
        updated_by=acting_user,
    )
    req.save()
    if cost:
        _record_points(
            acting_user, person_id=person_id, points=-cost,
            reason=f"Requested reward: {reward.name}", source_reward_request=req,
            transaction_type=_TxType.REWARD_REQUESTED,
        )
    events.reward_requested(req.id, req.household_id, person_id)
    return req


@transaction.atomic
def checkout_cart(acting_user: User, *, person_id: int, reward_ids: list[int]) -> list[MeridianRewardRequest]:
    """Request several rewards at once (cart checkout). All-or-nothing: if any item fails
    its stock/limit/balance check, the whole checkout rolls back."""
    if not reward_ids:
        raise MeridianError("Your cart is empty.")
    requests = []
    for reward_id in reward_ids:
        reward = MeridianReward.objects.filter(pk=reward_id).first()
        if reward is None:
            raise MeridianError("A reward in your cart no longer exists.")
        requests.append(request_reward(acting_user, reward, person_id=person_id))
    return requests


def _refund_reservation(acting_user: User, req: MeridianRewardRequest, *, transaction_type: str, reason: str) -> None:
    """Refund a reward's reserved points once, guarding against double refunds."""
    reserved = MeridianPointsEntry.all_objects.filter(
        source_reward_request=req, transaction_type=_TxType.REWARD_REQUESTED
    ).exists()
    already_refunded = MeridianPointsEntry.all_objects.filter(
        source_reward_request=req,
        transaction_type__in=(_TxType.REWARD_REFUNDED, _TxType.REWARD_CANCELLED_REFUND),
    ).exists()
    if reserved and not already_refunded and req.points_spent:
        _record_points(
            acting_user, person_id=req.requested_by_person_id, points=req.points_spent,
            reason=reason, source_reward_request=req, transaction_type=transaction_type,
        )


@transaction.atomic
def approve_reward_request(acting_user: User, req: MeridianRewardRequest) -> MeridianRewardRequest:
    """Approve a reward request. Points were already reserved at request time, so no further
    deduction happens (legacy parity)."""
    if req.status != MeridianRewardRequest.Status.PENDING:
        raise MeridianError("Only pending reward requests can be approved.")
    req.status = MeridianRewardRequest.Status.APPROVED
    req.approved_at = timezone.now()
    req.approved_by = acting_user
    req.updated_by = acting_user
    req.save()
    notifications.notify_person_id(
        req.requested_by_person_id, title="Reward approved",
        message=f"Your reward '{req.reward.name}' was approved!",
        level=notifications.Notification.Level.SUCCESS, source_node="meridian",
    )
    events.reward_approved(req.id, req.household_id, req.requested_by_person_id, req.points_spent)
    return req


@transaction.atomic
def reject_reward_request(acting_user: User, req: MeridianRewardRequest, *, reason: str = "") -> MeridianRewardRequest:
    """Reject a pending request and refund the reserved points."""
    if req.status != MeridianRewardRequest.Status.PENDING:
        raise MeridianError("Only pending reward requests can be rejected.")
    _refund_reservation(
        acting_user, req, transaction_type=_TxType.REWARD_REFUNDED,
        reason=f"Refunded rejected reward: {req.reward.name}",
    )
    req.status = MeridianRewardRequest.Status.REJECTED
    req.rejection_reason = reason
    req.updated_by = acting_user
    req.save()
    notifications.notify_person_id(
        req.requested_by_person_id, title="Reward not approved",
        message=f"'{req.reward.name}' was declined" + (f": {reason}" if reason else ".")
        + f" Your {req.points_spent} points were refunded.",
        level=notifications.Notification.Level.WARNING, source_node="meridian",
    )
    return req


@transaction.atomic
def cancel_reward_request(acting_user: User, req: MeridianRewardRequest) -> MeridianRewardRequest:
    """A person cancels their own pending request; reserved points are refunded."""
    if req.status != MeridianRewardRequest.Status.PENDING:
        raise MeridianError("Only pending reward requests can be cancelled.")
    _refund_reservation(
        acting_user, req, transaction_type=_TxType.REWARD_CANCELLED_REFUND,
        reason=f"Refunded cancelled reward: {req.reward.name}",
    )
    req.status = MeridianRewardRequest.Status.REJECTED
    req.rejection_reason = "Cancelled by requester."
    req.updated_by = acting_user
    req.save()
    return req
