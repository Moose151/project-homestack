"""Undo tests — routine deletion should be reversible rather than confirmed.

Confirmation interrupts every time, including the overwhelming majority of times the reader
was right. Undo interrupts nobody and rescues the rest — but only if restoring genuinely puts
the record back everywhere it was, which is what these assert.
"""
from datetime import date

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


class RestoreAcrossNodesTests(TestCase):
    """The rest of the nodes, brought onto the same contract.

    Each of these deletes is cheap, frequent and single-record — the rule for what gets undo.
    What varies is how much the delete took with it, and that is what each test pins down: a
    booking's deadline is hard-deleted rather than soft-deleted, and a bucket entry moved money.
    """

    def setUp(self):
        from apps.nodes.services import enable_node

        self.admin = _make_user("admin")
        _login(self.client, "admin")
        # The Home Wiki node key and its permission resource differ by an underscore.
        for node, resource in (
            ("atlas", "atlas"), ("home_wiki", "homewiki"), ("travel", "travel"),
            ("books", "books"), ("solace", "solace"),
        ):
            enable_node(self.admin, node)
            grant_user_permission(self.admin, f"{resource}.view")

    def _restore(self, record_type, record_id, client=None):
        return (client or self.client).post(
            reverse("undo-restore"),
            {"record_type": record_type, "record_id": record_id},
            content_type="application/json",
        )

    def _unlock(self):
        """Solace sits behind re-authentication; its undo has to pass the same gate."""
        self.client.post(
            reverse("auth-reauth"), {"password": "pass123!"}, content_type="application/json"
        )

    # --- Atlas ---

    def test_a_deleted_note_comes_back(self):
        from apps.atlas.models import AtlasNote
        from apps.atlas.services import create_note, delete_note

        note = create_note(self.admin, title="Wifi password", body="…")
        delete_note(self.admin, note)

        self.assertEqual(self._restore("AtlasNote", note.pk).status_code, 200)
        self.assertTrue(AtlasNote.objects.filter(pk=note.pk).exists())

    def test_a_deleted_contact_comes_back_with_its_birthday(self):
        from apps.atlas.models import AtlasContact
        from apps.atlas.services import create_contact, delete_contact

        contact = create_contact(
            self.admin, name="Aunt Jo", date_of_birth="1970-03-04", relationship="Aunt"
        )
        delete_contact(self.admin, contact)

        self.assertEqual(self._restore("AtlasContact", contact.pk).status_code, 200)
        self.assertTrue(AtlasContact.objects.filter(pk=contact.pk).exists())
        # The Calendar birthday is computed from the row on read rather than projected into a
        # CalendarEvent, so it returns with it — asserted through the endpoint Calendar calls,
        # rather than trusting the assumption.
        occurrences = self.client.get(
            reverse("atlas-birthday-occurrences"),
            {"start": "2027-01-01", "end": "2027-12-31"},
        ).json()
        self.assertTrue(any(row.get("contact_id") == contact.pk for row in occurrences))

    # --- Home Wiki ---

    def test_a_deleted_wiki_page_comes_back(self):
        from apps.home_wiki.models import WikiPage
        from apps.home_wiki.services import create_page, delete_page

        page = create_page(self.admin, title="Bin night", body="Thursdays")
        delete_page(self.admin, page)

        self.assertEqual(self._restore("WikiPage", page.pk).status_code, 200)
        self.assertTrue(WikiPage.objects.filter(pk=page.pk).exists())

    # --- Travel ---

    def test_a_deleted_idea_comes_back(self):
        from apps.travel.models import TravelIdea
        from apps.travel.services import create_idea, delete_idea

        idea = create_idea(self.admin, title="Tasmania", destination="Hobart")
        delete_idea(self.admin, idea)

        self.assertEqual(self._restore("TravelIdea", idea.pk).status_code, 200)
        self.assertTrue(TravelIdea.objects.filter(pk=idea.pk).exists())

    def test_a_deleted_itinerary_item_comes_back_with_its_calendar_entry(self):
        from apps.travel.models import TravelItineraryItem
        from apps.travel.services import create_itinerary_item, create_trip, delete_itinerary_item

        trip = create_trip(self.admin, title="Tasmania", destination="Hobart")
        item = create_itinerary_item(
            self.admin, trip, title="Salamanca Market", scheduled_date=date(2027, 2, 6)
        )
        delete_itinerary_item(self.admin, item)

        self.assertEqual(self._restore("TravelItineraryItem", item.pk).status_code, 200)
        restored = TravelItineraryItem.objects.get(pk=item.pk)
        self.assertIsNotNone(restored.calendar_event_id)
        self.assertTrue(CalendarEvent.objects.filter(pk=restored.calendar_event_id).exists())

    def test_a_deleted_booking_comes_back_with_the_deadline_it_took_with_it(self):
        """The deadline row is hard-deleted, so the restore has to make it again."""
        from apps.travel.models import BookingDeadline, TravelBooking
        from apps.travel.services import create_booking, create_trip, delete_booking

        trip = create_trip(self.admin, title="Tasmania", destination="Hobart")
        booking = create_booking(
            self.admin, trip, kind="flight", title="Flights",
            book_by=date(2027, 1, 10), start_at=_future(24 * 60),
        )
        self.assertTrue(BookingDeadline.objects.filter(booking=booking).exists())

        delete_booking(self.admin, booking)
        self.assertFalse(BookingDeadline.objects.filter(booking_id=booking.pk).exists())

        self.assertEqual(self._restore("TravelBooking", booking.pk).status_code, 200)
        restored = TravelBooking.objects.get(pk=booking.pk)
        # Two projections, both dropped by the delete: the booking's own dates, and the
        # separate "book by" deadline row.
        self.assertIsNotNone(restored.calendar_event_id)
        deadline = BookingDeadline.objects.filter(booking=restored).first()
        self.assertIsNotNone(deadline, "the 'book by' deadline must come back too")
        self.assertIsNotNone(deadline.calendar_event_id)

    # --- Books ---

    def test_a_deleted_personal_book_comes_back(self):
        from apps.books.models import PersonalBookEntry
        from apps.books.services import create_personal_entry, delete_personal_entry

        entry = create_personal_entry(
            self.admin, book={"title": "Piranesi", "author": "Susanna Clarke"}, status="reading"
        )
        delete_personal_entry(self.admin, entry)

        self.assertEqual(self._restore("PersonalBookEntry", entry.pk).status_code, 200)
        self.assertTrue(PersonalBookEntry.objects.filter(pk=entry.pk).exists())

    # --- Solace ---

    def test_a_deleted_purchase_comes_back_with_its_calendar_entry(self):
        from apps.solace.models import PlannedPurchase
        from apps.solace.services import create_purchase, delete_purchase

        purchase = create_purchase(self.admin, name="New mattress", target_date=_future(24 * 30))
        delete_purchase(self.admin, purchase)

        self._unlock()
        self.assertEqual(self._restore("PlannedPurchase", purchase.pk).status_code, 200)
        restored = PlannedPurchase.objects.get(pk=purchase.pk)
        self.assertIsNotNone(restored.calendar_event_id)
        self.assertTrue(CalendarEvent.objects.filter(pk=restored.calendar_event_id).exists())

    def test_a_deleted_payday_comes_back(self):
        from apps.solace.models import Payday
        from apps.solace.services import create_payday, delete_payday

        payday = create_payday(self.admin, title="Fortnightly", pay_at=_future(48))
        delete_payday(self.admin, payday)

        self._unlock()
        self.assertEqual(self._restore("Payday", payday.pk).status_code, 200)
        self.assertTrue(Payday.objects.filter(pk=payday.pk).exists())

    def test_a_deleted_bucket_entry_puts_the_money_back(self):
        from decimal import Decimal

        from apps.solace.models import BucketEntry, BudgetBucket
        from apps.solace.services import add_bucket_entry, create_bucket, delete_bucket_entry

        bucket = create_bucket(self.admin, name="Car service")
        entry = add_bucket_entry(self.admin, bucket, kind="deposit", amount="50.00")
        self.assertEqual(BudgetBucket.objects.get(pk=bucket.pk).current_amount, Decimal("50.00"))

        delete_bucket_entry(self.admin, entry)
        self.assertEqual(BudgetBucket.objects.get(pk=bucket.pk).current_amount, Decimal("0.00"))

        self._unlock()
        self.assertEqual(self._restore("BucketEntry", entry.pk).status_code, 200)
        self.assertTrue(BucketEntry.objects.filter(pk=entry.pk).exists())
        # The row without the balance would leave the bucket disagreeing with its own history.
        self.assertEqual(BudgetBucket.objects.get(pk=bucket.pk).current_amount, Decimal("50.00"))

    def test_a_deleted_balance_snapshot_comes_back(self):
        from apps.solace.models import AccountBalanceSnapshot
        from apps.solace.services import create_balance_snapshot, delete_balance_snapshot

        snapshot = create_balance_snapshot(self.admin, balance="1200.00")
        delete_balance_snapshot(self.admin, snapshot)

        self._unlock()
        self.assertEqual(self._restore("AccountBalanceSnapshot", snapshot.pk).status_code, 200)
        self.assertTrue(AccountBalanceSnapshot.objects.filter(pk=snapshot.pk).exists())

    def test_a_locked_sensitive_node_cannot_be_restored_into(self):
        """Undo must not be the one door into Solace that skips its lock."""
        from apps.solace.models import PlannedPurchase
        from apps.solace.services import create_purchase, delete_purchase

        purchase = create_purchase(self.admin, name="New mattress")
        delete_purchase(self.admin, purchase)

        # No re-authentication: the same session that may not open Solace may not undo into it.
        self.assertEqual(self._restore("PlannedPurchase", purchase.pk).status_code, 403)
        self.assertFalse(PlannedPurchase.objects.filter(pk=purchase.pk).exists())

    def test_a_club_book_is_deliberately_not_restorable(self):
        """Its queue rows are hard-deleted, so a restore would only be a half-restore."""
        self.assertEqual(self._restore("BookClubBook", 1).status_code, 404)
