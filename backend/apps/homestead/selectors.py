"""homestead selectors — read-only queries (Coding Standards §6, D9)."""
from __future__ import annotations

from datetime import timedelta

from django.db import connection
from django.db.models import Q
from django.utils import timezone

from apps.homestead.models import (
    Appliance,
    Improvement,
    MaintenanceTask,
    Property,
    ServiceProvider,
)
from apps.permissions.visibility import apply_visibility

_CLOSED_STATUSES = (Improvement.Status.DONE, Improvement.Status.CANCELLED)


def _search(qs, query: str, fields: list[str]):
    """Filter ``qs`` by ``query`` across ``fields`` (D9). Postgres FTS in prod, icontains on SQLite."""
    if connection.vendor == "postgresql":
        from django.contrib.postgres.search import SearchQuery, SearchVector
        return qs.annotate(_search=SearchVector(*fields)).filter(_search=SearchQuery(query))
    clause = Q()
    for field in fields:
        clause |= Q(**{f"{field}__icontains": query})
    return qs.filter(clause)


# ---------------------------------------------------------------------------
# Property
# ---------------------------------------------------------------------------

def list_properties(user=None):
    qs = Property.objects.order_by("-is_primary", "name")
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_property(pk: int) -> Property | None:
    return Property.objects.filter(pk=pk).first()


# ---------------------------------------------------------------------------
# Service providers
# ---------------------------------------------------------------------------

def list_providers(user=None):
    qs = ServiceProvider.objects.order_by("name")
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_provider(pk: int) -> ServiceProvider | None:
    return ServiceProvider.objects.filter(pk=pk).first()


# ---------------------------------------------------------------------------
# Appliances
# ---------------------------------------------------------------------------

def list_appliances(user=None, *, expiring_only: bool = False, within_days: int = 60,
                    limit: int | None = None):
    qs = Appliance.objects.order_by("name")
    if expiring_only:
        cutoff = timezone.now().date() + timedelta(days=within_days)
        qs = qs.filter(warranty_expires_at__isnull=False, warranty_expires_at__lte=cutoff)
        qs = qs.order_by("warranty_expires_at")
    if user is not None:
        qs = apply_visibility(qs, user)
    if limit is not None:
        qs = qs[:limit]
    return list(qs)


def get_appliance(pk: int) -> Appliance | None:
    return Appliance.objects.filter(pk=pk).first()


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------

def list_maintenance(user=None, *, due_only: bool = False, limit: int | None = None):
    qs = MaintenanceTask.objects.select_related("appliance", "provider").order_by(
        "next_due_at", "-updated_at"
    )
    if due_only:
        qs = qs.filter(next_due_at__isnull=False)
    if user is not None:
        qs = apply_visibility(qs, user)
    if limit is not None:
        qs = qs[:limit]
    return list(qs)


def get_maintenance(pk: int) -> MaintenanceTask | None:
    return MaintenanceTask.objects.filter(pk=pk).first()


# ---------------------------------------------------------------------------
# Improvements
# ---------------------------------------------------------------------------

def list_improvements(user=None, *, open_only: bool = False, limit: int | None = None):
    qs = Improvement.objects.order_by("-updated_at")
    if open_only:
        qs = qs.exclude(status__in=_CLOSED_STATUSES)
    if user is not None:
        qs = apply_visibility(qs, user)
    if limit is not None:
        qs = qs[:limit]
    return list(qs)


def get_improvement(pk: int) -> Improvement | None:
    return Improvement.objects.filter(pk=pk).first()


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search_homestead(user, query: str) -> dict:
    """Permission-filtered FTS across the Homestead surfaces (D9, Node Spec 25)."""
    appliances_qs = _search(
        Appliance.objects.all(), query,
        ["name", "brand", "model_number", "serial_number", "room", "notes"],
    )
    tasks_qs = _search(MaintenanceTask.objects.all(), query, ["title", "notes"])
    providers_qs = _search(
        ServiceProvider.objects.all(), query, ["name", "company", "notes"]
    )
    improvements_qs = _search(
        Improvement.objects.all(), query, ["title", "description", "room", "notes"]
    )
    if user is not None:
        appliances_qs = apply_visibility(appliances_qs, user)
        tasks_qs = apply_visibility(tasks_qs, user)
        providers_qs = apply_visibility(providers_qs, user)
        improvements_qs = apply_visibility(improvements_qs, user)
    return {
        "appliances": list(appliances_qs.order_by("name")),
        "maintenance": list(tasks_qs.order_by("next_due_at")),
        "providers": list(providers_qs.order_by("name")),
        "improvements": list(improvements_qs.order_by("-updated_at")),
    }
