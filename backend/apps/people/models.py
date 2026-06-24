"""
people.Person — a household member who may or may not have a login (D12).

Ownership/audit fields (created_by, updated_by) always reference a User.
Subjects/assignees across the system reference a Person — never a User directly.
"""
from django.conf import settings
from django.db import models

from apps.core.models import AllObjectsManager, HouseholdBaseModel, HouseholdManager


class Person(HouseholdBaseModel):
    """A household member (adult, child, or other) who can be assigned to tasks/events.

    Fields
    ------
    linked_user     Optional 1:1 link to accounts.User; set when this person has a login.
    display_name    The name shown in the UI (e.g. "Mum", "Finn").
    preferred_name  Shorter/nickname (e.g. "Fi"); falls back to display_name when blank.
    avatar          Colour name or image path used on avatar/profile displays.
    colour          Hex accent colour for this person's UI indicators (e.g. "#4A90E2").
    date_of_birth   Optional; used by nodes that care about age (Education, Health).
    profile_type    adult | child | other — governs kiosk eligibility and age gates.
    notes           Free-text notes visible to admin/manager only.

    Inherited from HouseholdBaseModel
    ----------------------------------
    household, created_at, updated_at, created_by, updated_by, deleted_at
    """

    class ProfileType(models.TextChoices):
        ADULT = "adult", "Adult"
        CHILD = "child", "Child"
        OTHER = "other", "Other"

    linked_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="person_profile",
    )
    display_name = models.CharField(max_length=100)
    preferred_name = models.CharField(max_length=100, blank=True, default="")
    avatar = models.CharField(max_length=255, blank=True, default="")
    colour = models.CharField(max_length=7, blank=True, default="")
    date_of_birth = models.DateField(null=True, blank=True)
    profile_type = models.CharField(
        max_length=10, choices=ProfileType.choices, default=ProfileType.ADULT
    )
    notes = models.TextField(blank=True, default="")

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "person"
        verbose_name_plural = "people"
        ordering = ["display_name"]

    def __str__(self) -> str:
        return self.display_name

    @property
    def name(self) -> str:
        """Preferred name if set, otherwise display name."""
        return self.preferred_name or self.display_name
