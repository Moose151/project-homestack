"""
Core models: the Household tenant anchor and the shared HouseholdBaseModel (D1, D12, D17).

Every user-facing model in HomeStack inherits `HouseholdBaseModel`, which provides:
  - the carried tenant column (`household`) — single household for now, but the scoping
    lives in ONE place so re-adding multi-household later touches only this manager (D1);
  - audit/ownership via `created_by` / `updated_by`, which are always **users** (D12);
  - soft delete (`deleted_at`), hidden by the default manager.

Record *subjects/assignees* are **people**, expressed by explicit `*_person` fields on the
concrete models — never here.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class Household(models.Model):
    """The single household this installation serves. Exactly one row in V1 (D1).

    Not a HouseholdBaseModel subclass — it is the tenant anchor the base model points at.
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    timezone = models.CharField(max_length=64, default="UTC")
    default_locale = models.CharField(max_length=16, default="en-us")
    # Accent colour for household-wide ("whole family") calendar events/tasks.
    family_colour = models.CharField(max_length=20, blank=True, default="#7C6F5A")
    # Household-level Calendar defaults (Core Calendar §15). A user's own saved prefs win;
    # these are the fallback for anyone who hasn't chosen their own.
    calendar_default_view = models.CharField(
        max_length=10,
        choices=[("month", "Month"), ("week", "Week"), ("day", "Day"), ("agenda", "Agenda")],
        default="month",
    )
    calendar_week_start = models.PositiveSmallIntegerField(
        choices=[(0, "Sunday"), (1, "Monday")], default=1
    )
    calendar_time_format = models.CharField(
        max_length=3, choices=[("12h", "12-hour"), ("24h", "24-hour")], default="12h"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "household"
        verbose_name_plural = "households"

    def __str__(self) -> str:
        return self.name


def get_active_household() -> "Household | None":
    """Return the single active household (D1). Used by services when stamping new rows.

    Returns None only before the seed migration has run (e.g. an empty test database).
    """
    return Household.objects.order_by("id").first()


class HouseholdQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        return self.filter(deleted_at__isnull=False)


class HouseholdManager(models.Manager):
    """Default manager for every HouseholdBaseModel.

    Excludes soft-deleted rows and is the single place where household scoping lives (D1).
    In single-household mode every row belongs to the one seeded household, so explicit
    household filtering is currently a structural no-op carried here deliberately — if
    multi-household is ever wanted, this manager is the only thing that changes.
    """

    def get_queryset(self) -> HouseholdQuerySet:
        return HouseholdQuerySet(self.model, using=self._db).alive()


class AllObjectsManager(models.Manager):
    """Escape hatch that includes soft-deleted rows (admin/restore/audit use)."""

    def get_queryset(self) -> HouseholdQuerySet:
        return HouseholdQuerySet(self.model, using=self._db)


class HouseholdBaseModel(models.Model):
    household = models.ForeignKey(
        Household,
        on_delete=models.PROTECT,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Ownership/audit always reference a USER (D12). Nullable so system/imported rows are valid.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def soft_delete(self) -> None:
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])

    def restore(self) -> None:
        self.deleted_at = None
        self.save(update_fields=["deleted_at", "updated_at"])
