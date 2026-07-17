from __future__ import annotations

from django.db import transaction

from apps.accounts.models import User
from apps.books.models import Book, BookClub, BookClubBook, BookClubMembership, BookClubQueueItem, BookRating, PersonalBookEntry
from apps.core.models import get_active_household


BOOK_FIELDS = {"title", "author", "pages", "genre", "isbn", "description", "cover_url"}
CLUB_FIELDS = {"name", "colour", "description"}


def _stamp(obj, acting_user: User):
    if not obj.household_id:
        obj.household = get_active_household()
    if not obj.created_by_id:
        obj.created_by = acting_user
    obj.updated_by = acting_user
    return obj


def get_or_create_book(acting_user: User, *, book_id: int | None = None, book: dict | None = None) -> Book:
    if book_id:
        return Book.objects.get(pk=book_id)
    assert book is not None
    defaults = {k: v for k, v in book.items() if k in BOOK_FIELDS}
    title = defaults.pop("title")
    author = defaults.pop("author", "")
    obj, created = Book.objects.get_or_create(
        title=title.strip(),
        author=author.strip(),
        defaults={"household": get_active_household(), "created_by": acting_user, "updated_by": acting_user, **defaults},
    )
    if not created:
        changed = False
        for key, value in defaults.items():
            if value not in (None, "") and not getattr(obj, key):
                setattr(obj, key, value)
                changed = True
        if changed:
            obj.updated_by = acting_user
            obj.save()
    return obj


def create_book(acting_user: User, **data) -> Book:
    obj = Book(household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data)
    obj.save()
    return obj


def update_book(acting_user: User, obj: Book, **data) -> Book:
    for key, value in data.items():
        if key in BOOK_FIELDS:
            setattr(obj, key, value)
    obj.updated_by = acting_user
    obj.save()
    return obj


def delete_book(acting_user: User, obj: Book) -> None:
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


def upsert_rating(acting_user: User, book: Book, *, rating=None, notes: str | None = None) -> BookRating:
    obj, _ = BookRating.objects.get_or_create(
        user=acting_user,
        book=book,
        defaults={"household": get_active_household(), "created_by": acting_user, "updated_by": acting_user},
    )
    if rating is not None:
        obj.rating = rating
    if notes is not None:
        obj.notes = notes
    obj.updated_by = acting_user
    obj.save()
    return obj


def create_personal_entry(acting_user: User, *, book_id: int | None = None, book: dict | None = None, status: str, position: int | None = None) -> PersonalBookEntry:
    book_obj = get_or_create_book(acting_user, book_id=book_id, book=book)
    obj, created = PersonalBookEntry.all_objects.get_or_create(
        user=acting_user,
        book=book_obj,
        defaults={
            "household": get_active_household(),
            "created_by": acting_user,
            "updated_by": acting_user,
            "status": status,
            "position": position or 0,
        },
    )
    if not created and obj.deleted_at is not None:
        obj.deleted_at = None
    obj.status = status
    if position is not None:
        obj.position = position
    obj.updated_by = acting_user
    obj.save()
    return obj


def update_personal_entry(acting_user: User, obj: PersonalBookEntry, **data) -> PersonalBookEntry:
    for key in ("status", "position"):
        if key in data:
            setattr(obj, key, data[key])
    obj.updated_by = acting_user
    obj.save()
    return obj


def delete_personal_entry(acting_user: User, obj: PersonalBookEntry) -> None:
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


def create_club(acting_user: User, **data) -> BookClub:
    with transaction.atomic():
        club = BookClub(household=get_active_household(), created_by=acting_user, updated_by=acting_user, **data)
        club.save()
        BookClubMembership.objects.create(
            household=get_active_household(), created_by=acting_user, updated_by=acting_user, club=club, user=acting_user
        )
    return club


def update_club(acting_user: User, club: BookClub, **data) -> BookClub:
    for key, value in data.items():
        if key in CLUB_FIELDS:
            setattr(club, key, value)
    club.updated_by = acting_user
    club.save()
    return club


def delete_club(acting_user: User, club: BookClub) -> None:
    club.updated_by = acting_user
    club.save(update_fields=["updated_by", "updated_at"])
    club.soft_delete()


def add_club_member(acting_user: User, club: BookClub, user: User) -> BookClubMembership:
    membership, created = BookClubMembership.all_objects.get_or_create(
        club=club,
        user=user,
        defaults={"household": get_active_household(), "created_by": acting_user, "updated_by": acting_user},
    )
    if not created and membership.deleted_at is not None:
        membership.deleted_at = None
        membership.updated_by = acting_user
        membership.save()
    return membership


def remove_club_member(acting_user: User, membership: BookClubMembership) -> None:
    membership.updated_by = acting_user
    membership.save(update_fields=["updated_by", "updated_at"])
    membership.soft_delete()


def create_club_book(acting_user: User, club: BookClub, *, book_id: int | None = None, book: dict | None = None, status: str, position: int | None = None) -> BookClubBook:
    book_obj = get_or_create_book(acting_user, book_id=book_id, book=book)
    obj, created = BookClubBook.all_objects.get_or_create(
        club=club,
        book=book_obj,
        defaults={
            "household": get_active_household(),
            "created_by": acting_user,
            "updated_by": acting_user,
            "added_by": acting_user,
            "status": status,
            "position": position or 0,
        },
    )
    if not created and obj.deleted_at is not None:
        obj.deleted_at = None
    obj.status = status
    if position is not None:
        obj.position = position
    obj.updated_by = acting_user
    obj.save()
    return obj


def update_club_book(acting_user: User, obj: BookClubBook, **data) -> BookClubBook:
    for key in ("status", "position"):
        if key in data:
            setattr(obj, key, data[key])
    obj.updated_by = acting_user
    obj.save()
    if obj.status != BookClubBook.Status.BACKLOG:
        BookClubQueueItem.objects.filter(club_book=obj).delete()
    return obj


def delete_club_book(acting_user: User, obj: BookClubBook) -> None:
    BookClubQueueItem.objects.filter(club_book=obj).delete()
    obj.updated_by = acting_user
    obj.save(update_fields=["updated_by", "updated_at"])
    obj.soft_delete()


def add_queue_item(acting_user: User, club: BookClub, club_book: BookClubBook, position: int | None = None) -> BookClubQueueItem:
    if club_book.club_id != club.id:
        raise ValueError("Book is not in this club.")
    if club_book.status != BookClubBook.Status.BACKLOG:
        club_book.status = BookClubBook.Status.BACKLOG
        club_book.updated_by = acting_user
        club_book.save()
    item, created = BookClubQueueItem.all_objects.get_or_create(
        club=club,
        club_book=club_book,
        defaults={"household": get_active_household(), "created_by": acting_user, "updated_by": acting_user, "position": position or 0},
    )
    if not created and item.deleted_at is not None:
        item.deleted_at = None
    if position is not None:
        item.position = position
        item.updated_by = acting_user
        item.save()
    return item


def update_queue_item(acting_user: User, item: BookClubQueueItem, **data) -> BookClubQueueItem:
    if "position" in data:
        item.position = data["position"]
    item.updated_by = acting_user
    item.save()
    return item


def delete_queue_item(acting_user: User, item: BookClubQueueItem) -> None:
    item.updated_by = acting_user
    item.save(update_fields=["updated_by", "updated_at"])
    item.soft_delete()
