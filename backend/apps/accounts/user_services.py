"""User-account management services (admin-only, D6/D12).

Distinct from auth (`services.py`): this creates and edits the **login accounts** themselves —
username, role, PIN, password, active state — and optionally links each to a household Person
(the assignee/subject side of the People-vs-Users split, D12).
"""
from __future__ import annotations

from django.db import transaction

from apps.accounts.models import User
from apps.core.models import get_active_household


class UserAdminError(Exception):
    """Domain error for user management (e.g. duplicate username, bad person link)."""


_CORE_FIELDS = {"display_name", "role", "email", "colour", "avatar", "is_child_account", "is_active"}


def _link_person(user: User, *, link_person_id: int | None, create_person: bool, acting_user: User) -> None:
    from apps.people.models import Person

    if link_person_id:
        person = Person.objects.filter(pk=link_person_id).first()
        if person is None:
            raise UserAdminError("Person to link was not found.")
        if person.linked_user_id and person.linked_user_id != user.id:
            raise UserAdminError("That person is already linked to another user.")
        person.linked_user = user
        person.colour = user.colour or person.colour
        person.display_name = user.display_name or person.display_name
        person.updated_by = acting_user
        person.save(update_fields=["linked_user", "colour", "display_name", "updated_by", "updated_at"])
    elif create_person:
        Person.objects.create(
            household=get_active_household(),
            display_name=user.display_name,
            profile_type=Person.ProfileType.CHILD if user.is_child_account else Person.ProfileType.ADULT,
            linked_user=user,
            colour=user.colour,
            created_by=acting_user,
            updated_by=acting_user,
        )


@transaction.atomic
def create_user_account(acting_user: User, *, username: str, display_name: str, pin: str = "",
                        password: str = "", link_person_id: int | None = None,
                        create_person: bool = False, **fields) -> User:
    username = (username or "").strip()
    if not username:
        raise UserAdminError("Username is required.")
    if not (display_name or "").strip():
        raise UserAdminError("Display name is required.")
    if User.all_objects.filter(username=username).exists():
        raise UserAdminError("That username is already taken.")

    extra = {k: v for k, v in fields.items() if k in _CORE_FIELDS and k != "display_name"}
    user = User.objects.create_user(
        username=username, display_name=display_name.strip(),
        password=password or None, created_by=acting_user, updated_by=acting_user, **extra,
    )
    if pin:
        user.set_pin(pin)
        user.save(update_fields=["pin_hash"])
    _link_person(user, link_person_id=link_person_id, create_person=create_person, acting_user=acting_user)
    return user


@transaction.atomic
def update_user_account(acting_user: User, user: User, *, pin: str | None = None,
                        password: str | None = None, **fields) -> User:
    if "username" in fields and fields["username"]:
        new_username = fields["username"].strip()
        if new_username != user.username and User.all_objects.filter(username=new_username).exists():
            raise UserAdminError("That username is already taken.")
        user.username = new_username
    for key, val in fields.items():
        if key in _CORE_FIELDS:
            setattr(user, key, val)
    if pin:  # only reset when a non-empty value is supplied
        user.set_pin(pin)
    if password:
        user.set_password(password)
    user.updated_by = acting_user
    user.save()
    # Keep the linked person in step: colour drives calendar event colouring; display_name
    # ensures the person record reflects the account's chosen name (D12).
    person = getattr(user, "person_profile", None)
    if person is not None:
        person_fields_changed = []
        if "colour" in fields and person.colour != user.colour:
            person.colour = user.colour
            person_fields_changed.append("colour")
        if "display_name" in fields and person.display_name != user.display_name:
            person.display_name = user.display_name
            person_fields_changed.append("display_name")
        if person_fields_changed:
            person.updated_by = acting_user
            person.save(update_fields=[*person_fields_changed, "updated_by", "updated_at"])
    return user


def deactivate_user(acting_user: User, user: User) -> User:
    """Disable login without deleting (preserves their ledger/history)."""
    user.is_active = False
    user.updated_by = acting_user
    user.save(update_fields=["is_active", "updated_by", "updated_at"])
    return user
