"""meridian models — native tasks, points, rewards and approvals (D13, D14, Node Spec 15).

Meridian is the household chores-and-rewards node: incentivised tasks with an
approval workflow, a per-person points ledger and a rewards shop. It is rebuilt
natively on shared services (Milestone 2) rather than integrated as an external app.

All content models inherit HouseholdBaseModel (household scoping, audit fields,
soft-delete). MeridianTask additionally implements CalendarSyncMixin so dated tasks
appear on the shared calendar via the scheduling helper — never by writing
CalendarEvent rows directly (D7).

Meridian holds no sensitive data (Node Spec 7), so no sensitive-node re-auth is
required. Points accrue per **person**; approvals are recorded against a **user** (D12).
"""
from __future__ import annotations

from datetime import date

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import AllObjectsManager, HouseholdBaseModel, HouseholdManager
from apps.scheduling.mixins import CalendarSyncMixin


class Visibility(models.TextChoices):
    PRIVATE = "private", "Private"
    HOUSEHOLD = "household", "Household"
    ROLE_RESTRICTED = "role_restricted", "Role Restricted"
    SENSITIVE = "sensitive", "Sensitive"


class MeridianCategory(HouseholdBaseModel):
    """A grouping for tasks or rewards (e.g. Bedroom, Pets, Reading, Treats).

    ``kind`` separates task categories from reward/shop categories (legacy parity: the standalone
    app had distinct TaskCategory and RewardCategory tables).
    """

    class Kind(models.TextChoices):
        TASK = "task", "Task"
        REWARD = "reward", "Reward"

    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.TASK, db_index=True)
    colour = models.CharField(max_length=7, blank=True, default="")
    icon = models.CharField(max_length=100, blank=True, default="")
    position = models.PositiveIntegerField(default=0)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "meridian category"
        verbose_name_plural = "meridian categories"
        ordering = ["position", "name"]

    def __str__(self) -> str:
        return self.name


class MeridianTask(CalendarSyncMixin, HouseholdBaseModel):
    """An incentivised task worth points once completed and approved.

    Lifecycle (the proven Meridian flow):
        AVAILABLE → (child/user completes) PENDING → (admin/manager) APPROVED | REJECTED
    Points are only awarded on approval. Dated tasks sync to the calendar (D7).
    """

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        PENDING = "pending", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    class CompletionBehavior(models.TextChoices):
        STAY_ACTIVE = "stay_active", "Stay active (repeatable)"
        HIDE_AFTER_APPROVAL = "hide_after_approval", "Hide after approval (one-off)"

    class CompletionScope(models.TextChoices):
        PER_PERSON = "per_person", "Each person separately"
        HOUSEHOLD = "household", "Household (first to complete)"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    points = models.PositiveIntegerField(default=0)
    category = models.ForeignKey(
        MeridianCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks",
    )
    assigned_to_person = models.ForeignKey(
        "people.Person",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_meridian_tasks",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.AVAILABLE
    )

    # Definition / behaviour (legacy parity, D19)
    completion_behavior = models.CharField(
        max_length=30, choices=CompletionBehavior.choices, default=CompletionBehavior.STAY_ACTIVE
    )
    completion_scope = models.CharField(
        max_length=20, choices=CompletionScope.choices, default=CompletionScope.PER_PERSON
    )
    availability_window = models.CharField(max_length=30, blank=True, default="always")
    is_active = models.BooleanField(default=True)  # published / shown to completers
    is_archived = models.BooleanField(default=False)  # hidden without soft-deleting

    # "Hot Tasks" — boosted/featured, optionally with bonus points on approval.
    is_hot = models.BooleanField(default=False)
    hot_bonus_points = models.PositiveIntegerField(default=0)
    hot_label = models.CharField(max_length=120, blank=True, default="")

    due_at = models.DateTimeField(null=True, blank=True)
    recurrence_rule = models.CharField(max_length=512, blank=True, default="")
    calendar_event_id = models.PositiveBigIntegerField(null=True, blank=True)

    # Completion is recorded against the PERSON who did the task (children are people).
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by_person = models.ForeignKey(
        "people.Person",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="completed_meridian_tasks",
    )
    # Approval/rejection is an account action, recorded against the USER (D12).
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_meridian_tasks",
    )
    rejection_reason = models.CharField(max_length=255, blank=True, default="")

    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "meridian task"
        ordering = ["-is_hot", "due_at", "-updated_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def is_complete(self) -> bool:
        return self.status in (self.Status.PENDING, self.Status.APPROVED)

    @property
    def award_value(self) -> int:
        """Points awarded on approval, including any hot-task bonus (legacy parity)."""
        total = self.points or 0
        if self.is_hot:
            total += self.hot_bonus_points or 0
        return total

    # --- CalendarSyncMixin contract (D7) ---

    def get_calendar_data(self) -> dict | None:
        if not self.due_at:
            return None
        return {
            "title": self.title,
            "start_at": self.due_at,
            "description": self.description,
            "recurrence_rule": self.recurrence_rule,
            "visibility": self.visibility,
            "assigned_to_person_id": self.assigned_to_person_id,
        }

    def get_calendar_node_key(self) -> str:
        return "meridian"


class MeridianPointsEntry(HouseholdBaseModel):
    """A single signed movement in a person's points ledger (the source of truth).

    Positive entries are awards (approved tasks, completed routines, allowance, manual
    adjustments); negative entries are spends/reservations (reward requests, goal/wishlist
    contributions). A person's **balance** is the sum of all their entries; their lifetime
    **total earned** is the sum of positive *earning* entries only (see services). Points are
    reserved when a reward/contribution is made and refunded if it is rejected or cancelled
    (legacy parity, D19).
    """

    class TransactionType(models.TextChoices):
        TASK_APPROVED = "task_approved", "Task approved"
        ROUTINE_COMPLETED = "routine_completed", "Routine completed"
        ALLOWANCE = "allowance", "Allowance"
        MANUAL_ADJUSTMENT = "manual_adjustment", "Manual adjustment"
        REWARD_REQUESTED = "reward_requested", "Reward requested (reserved)"
        REWARD_REFUNDED = "reward_refunded", "Reward refunded"
        REWARD_CANCELLED_REFUND = "reward_cancelled_refund", "Reward cancelled (refund)"
        GROUP_GOAL_CONTRIBUTION = "group_goal_contribution", "Group goal contribution"
        GROUP_GOAL_REFUND = "group_goal_refund", "Group goal refund"
        WISHLIST_CONTRIBUTION = "wishlist_contribution", "Wishlist contribution"
        WISHLIST_REFUND = "wishlist_refund", "Wishlist refund"

    #: Transaction types that count toward lifetime "total earned" (positive only).
    EARNING_TYPES = (
        TransactionType.TASK_APPROVED,
        TransactionType.ROUTINE_COMPLETED,
        TransactionType.ALLOWANCE,
        TransactionType.MANUAL_ADJUSTMENT,
    )

    person = models.ForeignKey(
        "people.Person", on_delete=models.CASCADE, related_name="meridian_points"
    )
    points = models.IntegerField()  # signed: + award, - spend
    transaction_type = models.CharField(
        max_length=40,
        choices=TransactionType.choices,
        default=TransactionType.MANUAL_ADJUSTMENT,
        db_index=True,
    )
    reason = models.CharField(max_length=255, blank=True, default="")
    source_task = models.ForeignKey(
        MeridianTask,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="points_entries",
    )
    source_reward_request = models.ForeignKey(
        "meridian.MeridianRewardRequest",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="points_entries",
    )
    source_routine = models.ForeignKey(
        "meridian.MeridianRoutine",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="points_entries",
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "meridian points entry"
        verbose_name_plural = "meridian points entries"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        sign = "+" if self.points >= 0 else ""
        return f"{self.person}: {sign}{self.points}"


class MeridianRoutine(HouseholdBaseModel):
    """A daily habit (e.g. brush teeth). Points are awarded immediately on completion —
    no approval — and consecutive-day completions build a streak (legacy parity, D19).
    """

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    points = models.PositiveIntegerField(default=1)
    assigned_to_person = models.ForeignKey(
        "people.Person",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_meridian_routines",
        help_text="If set, only this person sees/completes the routine; null = everyone.",
    )
    is_active = models.BooleanField(default=True)
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "meridian routine"
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title


class MeridianRoutineCompletion(HouseholdBaseModel):
    """One completion of a routine by a person on a calendar date.

    At most one non-voided completion per person/routine/date. Voided completions are
    excluded from streaks and the today-check (admin reset/rejection).
    """

    routine = models.ForeignKey(
        MeridianRoutine, on_delete=models.CASCADE, related_name="completions"
    )
    person = models.ForeignKey(
        "people.Person", on_delete=models.CASCADE, related_name="meridian_routine_completions"
    )
    completed_date = models.DateField(db_index=True)
    voided = models.BooleanField(default=False, db_index=True)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "meridian routine completion"
        ordering = ["-completed_date", "-id"]

    def __str__(self) -> str:
        return f"{self.person} · {self.routine} · {self.completed_date}"


class MeridianAllowance(HouseholdBaseModel):
    """Optional weekly allowance for a person — points awarded automatically by the scheduled
    command on a chosen weekday (legacy parity, D19; runs via cron per D5, not a live scheduler).
    """

    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    person = models.OneToOneField(
        "people.Person", on_delete=models.CASCADE, related_name="meridian_allowance"
    )
    amount = models.PositiveIntegerField(default=0)
    weekday = models.IntegerField(choices=Weekday.choices, default=Weekday.MONDAY)
    is_active = models.BooleanField(default=True)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "meridian allowance"

    def __str__(self) -> str:
        return f"{self.person}: {self.amount}/wk (day {self.weekday})"


class MeridianReward(HouseholdBaseModel):
    """An item in the rewards shop, purchasable with points (legacy parity, D19)."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    cost_points = models.PositiveIntegerField(default=0)
    icon = models.CharField(max_length=100, blank=True, default="")
    colour = models.CharField(max_length=7, blank=True, default="")
    image_url = models.URLField(max_length=500, blank=True, default="")
    is_active = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)

    # Display-only real-world references.
    price_estimate = models.CharField(max_length=60, blank=True, default="")
    store_url = models.URLField(max_length=500, blank=True, default="")

    # Stock + redemption limits.
    quantity = models.PositiveIntegerField(null=True, blank=True)  # None = unlimited
    allow_multiple_in_cart = models.BooleanField(default=False)
    disappear_when_empty = models.BooleanField(default=True)
    daily_limit_per_user = models.PositiveIntegerField(null=True, blank=True)  # None = no cap

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "meridian reward"
        ordering = ["cost_points", "name"]

    def __str__(self) -> str:
        return self.name

    def _held_request_count(self, *, person_id: int | None = None, on: date | None = None) -> int:
        qs = self.requests.filter(
            status__in=(
                MeridianRewardRequest.Status.PENDING,
                MeridianRewardRequest.Status.APPROVED,
            )
        )
        if person_id is not None:
            qs = qs.filter(requested_by_person_id=person_id)
        if on is not None:
            qs = qs.filter(created_at__date=on)
        return qs.count()

    def remaining_stock(self) -> int | None:
        """Units left, or None if unlimited. Pending + approved requests count as taken."""
        if self.quantity is None:
            return None
        return max(0, self.quantity - self._held_request_count())

    def daily_remaining_for_person(self, person_id: int) -> int | None:
        """How many more this person may redeem today, or None if uncapped."""
        if self.daily_limit_per_user is None:
            return None
        used = self._held_request_count(person_id=person_id, on=timezone.localdate())
        return max(0, self.daily_limit_per_user - used)


class MeridianRewardRequest(HouseholdBaseModel):
    """A person's request to redeem a reward; points are deducted on approval."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    reward = models.ForeignKey(
        MeridianReward, on_delete=models.CASCADE, related_name="requests"
    )
    requested_by_person = models.ForeignKey(
        "people.Person", on_delete=models.CASCADE, related_name="meridian_reward_requests"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    points_spent = models.PositiveIntegerField(default=0)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_meridian_reward_requests",
    )
    rejection_reason = models.CharField(max_length=255, blank=True, default="")

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "meridian reward request"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.requested_by_person} → {self.reward} ({self.status})"


class MeridianGroupGoal(HouseholdBaseModel):
    """A shared target the household contributes points toward (legacy parity, D19)."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        FUNDED = "funded", "Funded"
        ARCHIVED = "archived", "Archived"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    target_points = models.PositiveIntegerField(default=0)
    price_estimate = models.CharField(max_length=60, blank=True, default="")
    store_url = models.URLField(max_length=500, blank=True, default="")
    image_url = models.URLField(max_length=500, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    is_active = models.BooleanField(default=True)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "meridian group goal"
        ordering = ["status", "title"]

    def __str__(self) -> str:
        return self.title

    def total_contributed(self) -> int:
        agg = self.contributions.filter(
            status=MeridianGroupGoalContribution.Status.ACTIVE
        ).aggregate(total=models.Sum("amount"))
        return agg["total"] or 0

    def remaining_points(self) -> int:
        return max(0, self.target_points - self.total_contributed())

    def progress_percentage(self) -> int:
        if self.target_points <= 0:
            return 0
        return min(100, int((self.total_contributed() / self.target_points) * 100))

    def is_funded(self) -> bool:
        return self.total_contributed() >= self.target_points


class MeridianGroupGoalContribution(HouseholdBaseModel):
    """A person's points contribution toward a group goal (refundable)."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        REFUNDED = "refunded", "Refunded"

    goal = models.ForeignKey(
        MeridianGroupGoal, on_delete=models.CASCADE, related_name="contributions"
    )
    person = models.ForeignKey(
        "people.Person", on_delete=models.CASCADE, related_name="meridian_goal_contributions"
    )
    amount = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "meridian group goal contribution"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.person} → {self.goal}: {self.amount}"


class MeridianWishlistRequest(HouseholdBaseModel):
    """A person's request for an item to be added to their wishlist (admin approves)."""

    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    person = models.ForeignKey(
        "people.Person", on_delete=models.CASCADE, related_name="meridian_wishlist_requests"
    )
    requested_name = models.CharField(max_length=255)
    requested_description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)
    rejection_reason = models.CharField(max_length=255, blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="reviewed_meridian_wishlist_requests",
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "meridian wishlist request"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.person}: {self.requested_name} ({self.status})"


class MeridianWishlistItem(HouseholdBaseModel):
    """An approved wishlist item owned by a person, funded by their contributions over time."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        FUNDED = "funded", "Funded"
        FULFILLED = "fulfilled", "Fulfilled"

    person = models.ForeignKey(
        "people.Person", on_delete=models.CASCADE, related_name="meridian_wishlist_items"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    point_cost = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    is_active = models.BooleanField(default=True)
    price_estimate = models.CharField(max_length=60, blank=True, default="")
    store_url = models.URLField(max_length=500, blank=True, default="")
    image_url = models.URLField(max_length=500, blank=True, default="")

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "meridian wishlist item"
        ordering = ["status", "name"]

    def __str__(self) -> str:
        return f"{self.person}: {self.name}"

    def total_saved(self) -> int:
        agg = self.contributions.filter(
            status=MeridianWishlistContribution.Status.ACTIVE
        ).aggregate(total=models.Sum("amount"))
        return agg["total"] or 0

    def remaining_points(self) -> int:
        return max(0, self.point_cost - self.total_saved())

    def progress_percentage(self) -> int:
        if self.point_cost <= 0:
            return 0
        return min(100, int((self.total_saved() / self.point_cost) * 100))

    def is_funded(self) -> bool:
        return self.total_saved() >= self.point_cost


class MeridianWishlistContribution(HouseholdBaseModel):
    """A person's points contribution toward their wishlist item (refundable)."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        REFUNDED = "refunded", "Refunded"

    item = models.ForeignKey(
        MeridianWishlistItem, on_delete=models.CASCADE, related_name="contributions"
    )
    person = models.ForeignKey(
        "people.Person", on_delete=models.CASCADE, related_name="meridian_wishlist_contributions"
    )
    amount = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "meridian wishlist contribution"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.person} → {self.item}: {self.amount}"
