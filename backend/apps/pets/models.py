"""pets models — pet profiles, treatment reminders, vet appointments (Node Spec 13).

Milestone 3 V1 slice (§16): pet profiles · treatment reminders · vet appointments · calendar
integration · Hub widget · FTS · basic permissions. Medication is modelled as a treatment
type; weight logs / feeding schedules / insurance tracking are future enhancements (§17).

All models inherit HouseholdBaseModel (household scoping, audit fields, soft-delete). No fixed
pet count or names (D15). PetTreatment and PetAppointment implement CalendarSyncMixin so due
dates appear on the shared calendar without ever writing CalendarEvent rows directly (D7);
recurring treatments carry `recurrence_rule` (RRULE, D8).
"""
from __future__ import annotations

from django.db import models

from apps.core.models import AllObjectsManager, HouseholdBaseModel, HouseholdManager
from apps.scheduling.mixins import CalendarSyncMixin


class Visibility(models.TextChoices):
    PRIVATE = "private", "Private"
    HOUSEHOLD = "household", "Household"
    ROLE_RESTRICTED = "role_restricted", "Role Restricted"
    SENSITIVE = "sensitive", "Sensitive"


class Pet(HouseholdBaseModel):
    """A household pet and its reference details."""

    class Species(models.TextChoices):
        DOG = "dog", "Dog"
        CAT = "cat", "Cat"
        BIRD = "bird", "Bird"
        FISH = "fish", "Fish"
        REPTILE = "reptile", "Reptile"
        SMALL_MAMMAL = "small_mammal", "Small mammal"
        OTHER = "other", "Other"

    name = models.CharField(max_length=120)
    species = models.CharField(max_length=20, choices=Species.choices, default=Species.OTHER)
    breed = models.CharField(max_length=120, blank=True, default="")
    avatar = models.CharField(max_length=255, blank=True, default="")  # emoji or image ref
    colour = models.CharField(max_length=40, blank=True, default="")
    date_of_birth = models.DateField(null=True, blank=True)
    adoption_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    vet_name = models.CharField(max_length=255, blank=True, default="")
    vet_phone = models.CharField(max_length=50, blank=True, default="")
    microchip_number = models.CharField(max_length=50, blank=True, default="")
    insurance_provider = models.CharField(max_length=255, blank=True, default="")
    insurance_policy_number = models.CharField(max_length=100, blank=True, default="")
    food_notes = models.TextField(blank=True, default="")
    is_archived = models.BooleanField(default=False)
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "pet"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class PetTreatment(CalendarSyncMixin, HouseholdBaseModel):
    """A recurring or one-off pet-care treatment (flea, worming, vaccination, medication, …).

    `next_due_at` is the source of truth for the reminder and drives the calendar event.
    Marking a treatment done advances `next_due_at` to the next RRULE occurrence (D8).
    """

    class TreatmentType(models.TextChoices):
        FLEA = "flea", "Flea"
        WORMING = "worming", "Worming"
        VACCINATION = "vaccination", "Vaccination"
        MEDICATION = "medication", "Medication"
        GROOMING = "grooming", "Grooming"
        OTHER = "other", "Other"

    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="treatments")
    treatment_type = models.CharField(
        max_length=20, choices=TreatmentType.choices, default=TreatmentType.OTHER
    )
    name = models.CharField(max_length=255, blank=True, default="")  # e.g. product/medication name
    last_done_at = models.DateTimeField(null=True, blank=True)
    next_due_at = models.DateTimeField(null=True, blank=True)
    recurrence_rule = models.CharField(max_length=512, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    calendar_event_id = models.PositiveBigIntegerField(null=True, blank=True)
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "pet treatment"
        ordering = ["next_due_at", "-updated_at"]

    def __str__(self) -> str:
        return f"{self.get_treatment_type_display()} — {self.pet}"

    @property
    def display_name(self) -> str:
        label = self.get_treatment_type_display()
        return f"{label}: {self.name}" if self.name else label

    @property
    def is_overdue(self) -> bool:
        from django.utils import timezone
        return bool(self.next_due_at and self.next_due_at < timezone.now())

    # --- CalendarSyncMixin contract ---

    def get_calendar_data(self) -> dict | None:
        if not self.next_due_at:
            return None
        return {
            "title": f"{self.pet.name}: {self.display_name}",
            "start_at": self.next_due_at,
            "is_all_day": True,
            "description": self.notes,
            "recurrence_rule": self.recurrence_rule,
            "visibility": self.visibility,
        }

    def get_calendar_node_key(self) -> str:
        return "pets"


class PetAppointment(CalendarSyncMixin, HouseholdBaseModel):
    """A vet or grooming appointment for a pet."""

    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="appointments")
    title = models.CharField(max_length=255, blank=True, default="")  # e.g. "Annual check-up"
    provider = models.CharField(max_length=255, blank=True, default="")  # vet/clinic
    location = models.CharField(max_length=255, blank=True, default="")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    calendar_event_id = models.PositiveBigIntegerField(null=True, blank=True)
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "pet appointment"
        ordering = ["start_at"]

    def __str__(self) -> str:
        return f"{self.title or 'Appointment'} — {self.pet}"

    @property
    def display_title(self) -> str:
        return self.title or (f"{self.provider} visit" if self.provider else "Vet appointment")

    # --- CalendarSyncMixin contract ---

    def get_calendar_data(self) -> dict | None:
        if not self.start_at:
            return None
        return {
            "title": f"{self.pet.name}: {self.display_title}",
            "start_at": self.start_at,
            "end_at": self.end_at,
            "description": self.notes or self.location,
            "visibility": self.visibility,
        }

    def get_calendar_node_key(self) -> str:
        return "pets"
