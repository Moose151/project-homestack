"""pets selectors — read-only queries (Coding Standards §6, D9)."""
from __future__ import annotations

from django.db import connection
from django.db.models import Q
from django.utils import timezone

from apps.pets.models import Pet, PetAppointment, PetTreatment
from apps.permissions.visibility import apply_visibility


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
# Pets
# ---------------------------------------------------------------------------

def list_pets(user=None, *, include_archived: bool = False):
    qs = Pet.objects.order_by("name")
    if not include_archived:
        qs = qs.filter(is_archived=False)
    if user is not None:
        qs = apply_visibility(qs, user)
    return list(qs)


def get_pet(pk: int) -> Pet | None:
    return Pet.objects.filter(pk=pk).first()


# ---------------------------------------------------------------------------
# Treatments
# ---------------------------------------------------------------------------

def list_treatments(
    user=None, *, pet_id: int | None = None, due_only: bool = False,
    limit: int | None = None,
):
    qs = PetTreatment.objects.select_related("pet").order_by("next_due_at", "-updated_at")
    if pet_id is not None:
        qs = qs.filter(pet_id=pet_id)
    if due_only:
        qs = qs.filter(next_due_at__isnull=False)
    if user is not None:
        qs = apply_visibility(qs, user)
    if limit is not None:
        qs = qs[:limit]
    return list(qs)


def get_treatment(pk: int) -> PetTreatment | None:
    return PetTreatment.objects.filter(pk=pk).first()


# ---------------------------------------------------------------------------
# Appointments
# ---------------------------------------------------------------------------

def list_appointments(
    user=None, *, pet_id: int | None = None, upcoming_only: bool = False,
    limit: int | None = None,
):
    qs = PetAppointment.objects.select_related("pet").order_by("start_at")
    if pet_id is not None:
        qs = qs.filter(pet_id=pet_id)
    if upcoming_only:
        qs = qs.filter(start_at__gte=timezone.now())
    if user is not None:
        qs = apply_visibility(qs, user)
    if limit is not None:
        qs = qs[:limit]
    return list(qs)


def get_appointment(pk: int) -> PetAppointment | None:
    return PetAppointment.objects.filter(pk=pk).first()


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search_pets(user, query: str) -> dict:
    """Permission-filtered FTS across pets, treatments and appointments (D9, Node Spec 12)."""
    pets_qs = _search(Pet.objects.all(), query, ["name", "breed", "vet_name", "notes"])
    treatments_qs = _search(PetTreatment.objects.select_related("pet"), query, ["name", "notes"])
    appointments_qs = _search(
        PetAppointment.objects.select_related("pet"), query, ["title", "provider", "location", "notes"]
    )
    if user is not None:
        pets_qs = apply_visibility(pets_qs, user)
        treatments_qs = apply_visibility(treatments_qs, user)
        appointments_qs = apply_visibility(appointments_qs, user)
    return {
        "pets": list(pets_qs.order_by("name")),
        "treatments": list(treatments_qs.order_by("next_due_at")),
        "appointments": list(appointments_qs.order_by("start_at")),
    }
