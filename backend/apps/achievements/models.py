"""achievements models — a shared, cross-node badge system (D20).

Badges recognise activity across *all* nodes, not just Meridian. The app stays decoupled from
the nodes that earn them (D4): it never imports another node's models. Instead it listens to
domain events on the bus and keeps its **own** per-person aggregates (`AchievementCounter`), so
it can evaluate count- and metric-based criteria without reaching into Meridian/Education/etc.

  Badge             — global catalogue (like nodes/permissions): code + display + which node
                      `source` defines it. Seeded per node.
  PersonBadge       — a badge earned by a person (household-scoped, one row per person+badge).
  AchievementCounter— the app's own running tally per person+key, updated from events.
"""
from __future__ import annotations

from django.db import models

from apps.core.models import AllObjectsManager, HouseholdBaseModel, HouseholdManager


class Badge(models.Model):
    """Global badge catalogue. Plain model (no household) like `nodes.Node`."""

    code = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True, default="")
    icon = models.CharField(max_length=20, blank=True, default="🏅")
    source = models.CharField(
        max_length=40, blank=True, default="",
        help_text="Node key that defines this badge, e.g. 'meridian'.",
    )
    position = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "badge"
        ordering = ["source", "position", "code"]

    def __str__(self) -> str:
        return f"{self.icon} {self.name}"


class PersonBadge(HouseholdBaseModel):
    """A badge a person has earned (household-scoped). One per person+badge."""

    person = models.ForeignKey(
        "people.Person", on_delete=models.CASCADE, related_name="badges"
    )
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name="awards")
    earned_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=40, blank=True, default="")

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "person badge"
        ordering = ["-earned_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["person", "badge"], name="unique_person_badge")
        ]

    def __str__(self) -> str:
        return f"{self.person} earned {self.badge.code}"


class AchievementCounter(HouseholdBaseModel):
    """The app's own per-person tally for a metric key (e.g. 'meridian.tasks_approved').

    Keeping our own counters is what lets achievements stay fully decoupled from the nodes
    that emit events (D4) — we never query Meridian to count approved tasks.
    """

    person = models.ForeignKey(
        "people.Person", on_delete=models.CASCADE, related_name="achievement_counters"
    )
    key = models.CharField(max_length=80, db_index=True)
    value = models.IntegerField(default=0)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "achievement counter"
        ordering = ["person_id", "key"]
        constraints = [
            models.UniqueConstraint(fields=["person", "key"], name="unique_person_counter")
        ]

    def __str__(self) -> str:
        return f"{self.person} · {self.key}={self.value}"
