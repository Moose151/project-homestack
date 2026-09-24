"""Undo tests — routine deletion should be reversible rather than confirmed.

Confirmation interrupts every time, including the overwhelming majority of times the reader
was right. Undo interrupts nobody and rescues the rest — but only if restoring genuinely puts
the record back everywhere it was, which is what these assert.
"""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.permissions.services import deny_user_permission, grant_user_permission
from apps.scheduling.models import CalendarEvent


def _make_user(username, role=User.Role.ADMIN) -> User:
    user = User.objects.create_user(
        username=username, display_name=username.capitalize(), role=role, password="pass123!"
    )
    user.set_pin("1234")
    user.save()
    return user


def _login(client, username, pin="1234"):
    client.post(
        reverse("auth-pin-login"),
        {"username": username, "pin": pin},
        content_type="application/json",
    )


def _future(hours=24):
    return timezone.now() + timezone.timedelta(hours=hours)


class RestoreRecordTests(TestCase):
    def setUp(self):
        from apps.nodes.services import enable_node

        self.admin = _make_user("admin")
        _login(self.client, "admin")
        for node in ("education", "atlas", "homestead", "pets"):
            enable_node(self.admin, node)
            grant_user_permission(self.admin, f"{node}.view")

    def _restore(self, record_type, record_id, client=None):
        return (client or self.client).post(
            reverse("undo-restore"),
            {"record_type": record_type, "record_id": record_id},
            content_type="application/json",
        )

    def test_a_deleted_assignment_comes_back_with_its_calendar_entry(self):
        from apps.education.models import EducationAssessment
        from apps.education.services import create_assessment, delete_assessment

        assessment = create_assessment(self.admin, title="Research report", due_at=_future())
        delete_assessment(self.admin, assessment)
        self.assertFalse(EducationAssessment.objects.filter(pk=assessment.pk).exists())

        response = self._restore("EducationAssessment", assessment.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["noun"], "assignment")

        restored = EducationAssessment.objects.get(pk=assessment.pk)
        # Restoring the row alone would leave it present in its node but missing from the
        # household timeline — the record would be back, but only half back.
        self.assertIsNotNone(restored.calendar_event_id)
        self.assertTrue(CalendarEvent.objects.filter(pk=restored.calendar_event_id).exists())

    def test_a_deleted_todo_comes_back(self):
        from apps.atlas.models import AtlasListItem
        from apps.atlas.services import create_atlas_list, create_list_item, delete_list_item

        todo_list = create_atlas_list(self.admin, title="Household", list_type="todo")
        item = create_list_item(self.admin, todo_list, title="Put the bins out", due_at=_future())
        delete_list_item(self.admin, item)
        self.assertFalse(AtlasListItem.objects.filter(pk=item.pk).exists())

        self.assertEqual(self._restore("AtlasListItem", item.pk).status_code, 200)
        self.assertTrue(AtlasListItem.objects.filter(pk=item.pk).exists())

    def test_a_deleted_maintenance_task_comes_back(self):
        from apps.homestead.models import MaintenanceTask
        from apps.homestead.services import create_maintenance, delete_maintenance

        job = create_maintenance(self.admin, title="Service the boiler", next_due_at=_future())
        delete_maintenance(self.admin, job)

        self.assertEqual(self._restore("MaintenanceTask", job.pk).status_code, 200)
        self.assertTrue(MaintenanceTask.objects.filter(pk=job.pk).exists())

    def test_a_deleted_pet_treatment_comes_back(self):
        from apps.pets.models import PetTreatment
        from apps.pets.services import create_pet, create_treatment, delete_treatment

        pet = create_pet(self.admin, name="Rosie", species="dog")
        treatment = create_treatment(
            self.admin, pet=pet, treatment_type="flea", next_due_at=_future()
        )
        delete_treatment(self.admin, treatment)

        self.assertEqual(self._restore("PetTreatment", treatment.pk).status_code, 200)
        self.assertTrue(PetTreatment.objects.filter(pk=treatment.pk).exists())

    # --- boundaries ---

    def test_restoring_twice_is_harmless(self):
        """An Undo toast can be tapped twice, or two devices can race it."""
        from apps.education.services import create_assessment, delete_assessment

        assessment = create_assessment(self.admin, title="Research report", due_at=_future())
        delete_assessment(self.admin, assessment)

        self.assertEqual(self._restore("EducationAssessment", assessment.pk).status_code, 200)
        self.assertEqual(self._restore("EducationAssessment", assessment.pk).status_code, 404)

    def test_a_record_type_not_in_the_registry_is_refused(self):
        """This is a bounded list, not a general-purpose trash can."""
        self.assertEqual(self._restore("Person", 1).status_code, 404)
        self.assertEqual(self._restore("", 1).status_code, 404)

    def test_a_nonexistent_id_is_refused(self):
        self.assertEqual(self._restore("EducationAssessment", 999999).status_code, 404)
        self.assertEqual(self._restore("EducationAssessment", "not-a-number").status_code, 404)

    def test_restoring_needs_the_same_right_as_deleting(self):
        from apps.education.services import create_assessment, delete_assessment

        assessment = create_assessment(self.admin, title="Research report", due_at=_future())
        delete_assessment(self.admin, assessment)

        viewer = _make_user("viewer", User.Role.USER)
        grant_user_permission(viewer, "education.view")
        deny_user_permission(viewer, "education.delete")
        other = self.client_class()
        _login(other, "viewer")

        response = self._restore("EducationAssessment", assessment.pk, client=other)
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_callers_are_rejected(self):
        anon = self.client_class()
        response = anon.post(
            reverse("undo-restore"),
            {"record_type": "EducationAssessment", "record_id": 1},
            content_type="application/json",
        )
        self.assertIn(response.status_code, (401, 403))
