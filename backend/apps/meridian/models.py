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

from django.conf import settings
from django.db import models

from apps.core.models import AllObjectsManager, HouseholdBaseModel, HouseholdManager
from apps.scheduling.mixins import CalendarSyncMixin


class Visibility(models.TextChoices):
    PRIVATE = "private", "Private"
    HOUSEHOLD = "household", "Household"
    ROLE_RESTRICTED = "role_restricted", "Role Restricted"
    SENSITIVE = "sensitive", "Sensitive"


class MeridianCategory(HouseholdBaseModel):
    """A grouping for tasks (e.g. Bedroom, Pets, Reading)."""

    name = models.CharField(max_length=100)
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
    is_hot = models.BooleanField(default=False)  # "Hot Tasks" — boosted/featured

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
    """A single signed movement in a person's points ledger.

    Positive entries are awards (approved tasks, manual adjustments); negative entries
    are spends (approved reward requests). A person's balance is the sum of their entries.
    """

    person = models.ForeignKey(
        "people.Person", on_delete=models.CASCADE, related_name="meridian_points"
    )
    points = models.IntegerField()  # signed: + award, - spend
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

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "meridian points entry"
        verbose_name_plural = "meridian points entries"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        sign = "+" if self.points >= 0 else ""
        return f"{self.person}: {sign}{self.points}"


class MeridianReward(HouseholdBaseModel):
    """An item in the rewards shop, purchasable with points."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    cost_points = models.PositiveIntegerField(default=0)
    icon = models.CharField(max_length=100, blank=True, default="")
    colour = models.CharField(max_length=7, blank=True, default="")
    is_active = models.BooleanField(default=True)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "meridian reward"
        ordering = ["cost_points", "name"]

    def __str__(self) -> str:
        return self.name


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
