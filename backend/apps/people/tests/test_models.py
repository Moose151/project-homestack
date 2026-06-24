"""
people model tests — Phase 1.4 (D12).

Covers:
- Person creation via services.create_person (household stamp, audit fields).
- Soft-delete behaviour via HouseholdManager.
- ProfileType choices.
- __str__ and .name property.
- linked_user OneToOne constraint.
"""
from django.test import TestCase

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.people.models import Person
from apps.people.services import create_person, delete_person, update_person


def _make_user(username="actor", display_name="Actor") -> User:
    return User.objects.create_user(username=username, display_name=display_name, password="pass!")


def _make_person(acting_user, **kwargs) -> Person:
    defaults = {"display_name": "Test Person", "profile_type": Person.ProfileType.ADULT}
    defaults.update(kwargs)
    return create_person(acting_user, **defaults)


class PersonCreationTests(TestCase):
    def setUp(self):
        self.actor = _make_user()

    def test_person_belongs_to_seeded_household(self):
        person = _make_person(self.actor)
        self.assertEqual(person.household, get_active_household())

    def test_created_by_set_to_acting_user(self):
        person = _make_person(self.actor)
        self.assertEqual(person.created_by, self.actor)

    def test_updated_by_set_to_acting_user(self):
        person = _make_person(self.actor)
        self.assertEqual(person.updated_by, self.actor)

    def test_default_profile_type_adult(self):
        person = _make_person(self.actor)
        self.assertEqual(person.profile_type, Person.ProfileType.ADULT)

    def test_child_profile_type(self):
        person = _make_person(self.actor, profile_type=Person.ProfileType.CHILD)
        self.assertEqual(person.profile_type, Person.ProfileType.CHILD)

    def test_str_returns_display_name(self):
        person = _make_person(self.actor, display_name="Finn")
        self.assertEqual(str(person), "Finn")

    def test_name_returns_preferred_name_when_set(self):
        person = _make_person(self.actor, display_name="Finnegan", preferred_name="Finn")
        self.assertEqual(person.name, "Finn")

    def test_name_falls_back_to_display_name(self):
        person = _make_person(self.actor, display_name="Finnegan", preferred_name="")
        self.assertEqual(person.name, "Finnegan")

    def test_linked_user_nullable(self):
        person = _make_person(self.actor)
        self.assertIsNone(person.linked_user)

    def test_linked_user_can_be_set(self):
        user = _make_user(username="linked", display_name="Linked")
        person = _make_person(self.actor, linked_user=user)
        self.assertEqual(person.linked_user, user)

    def test_linked_user_is_one_to_one(self):
        user = _make_user(username="linked", display_name="Linked")
        _make_person(self.actor, linked_user=user)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Person.objects.create(
                household=get_active_household(),
                linked_user=user,
                display_name="Duplicate",
                profile_type=Person.ProfileType.ADULT,
            )


class PersonSoftDeleteTests(TestCase):
    def setUp(self):
        self.actor = _make_user()

    def test_soft_delete_excludes_from_default_manager(self):
        person = _make_person(self.actor)
        delete_person(self.actor, person)
        self.assertFalse(Person.objects.filter(pk=person.pk).exists())

    def test_soft_deleted_visible_via_all_objects(self):
        person = _make_person(self.actor)
        delete_person(self.actor, person)
        self.assertTrue(Person.all_objects.filter(pk=person.pk).exists())

    def test_restore_brings_person_back(self):
        person = _make_person(self.actor)
        delete_person(self.actor, person)
        person.restore()
        self.assertTrue(Person.objects.filter(pk=person.pk).exists())


class PersonUpdateTests(TestCase):
    def setUp(self):
        self.actor = _make_user()
        self.person = _make_person(self.actor, display_name="Original")

    def test_update_changes_display_name(self):
        updated = update_person(self.actor, self.person, display_name="Updated")
        self.assertEqual(updated.display_name, "Updated")

    def test_update_stamps_updated_by(self):
        other = _make_user(username="other", display_name="Other")
        updated = update_person(other, self.person, display_name="Changed")
        self.assertEqual(updated.updated_by, other)
