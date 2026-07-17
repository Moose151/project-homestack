from __future__ import annotations

from django.db import connection
from django.db.models import Avg, Prefetch, Q

from apps.books.models import Book, BookClub, BookClubBook, BookClubMembership, BookClubQueueItem, BookRating, PersonalBookEntry


def _search(qs, query: str, fields: list[str]):
    if connection.vendor == "postgresql":
        from django.contrib.postgres.search import SearchQuery, SearchVector
        return qs.annotate(_search=SearchVector(*fields)).filter(_search=SearchQuery(query))
    clause = Q()
    for field in fields:
        clause |= Q(**{f"{field}__icontains": query})
    return qs.filter(clause)


def list_books(query: str = ""):
    qs = Book.objects.order_by("title", "author")
    if query:
        qs = _search(qs, query, ["title", "author", "genre", "isbn", "description"])
    return list(qs[:100])


def get_book(pk: int) -> Book | None:
    return Book.objects.filter(pk=pk).first()


def list_personal_entries(user, *, include_clubs: bool = True):
    entries = list(
        PersonalBookEntry.objects.select_related("book")
        .filter(user=user)
        .order_by("status", "position", "created_at")
    )
    rating_map = {
        r.book_id: r for r in BookRating.objects.filter(user=user, book_id__in=[e.book_id for e in entries])
    }
    for entry in entries:
        entry.book_rating = rating_map.get(entry.book_id)

    if not include_clubs:
        return {"personal": entries, "club": []}

    club_entries = list(
        BookClubBook.objects.select_related("book", "club", "added_by")
        .filter(club__memberships__user=user)
        .order_by("status", "position", "created_at")
        .distinct()
    )
    club_book_ids = [e.book_id for e in club_entries]
    club_rating_map = {r.book_id: r for r in BookRating.objects.filter(user=user, book_id__in=club_book_ids)}
    for entry in club_entries:
        entry.book_rating = club_rating_map.get(entry.book_id)
    return {"personal": entries, "club": club_entries}


def get_personal_entry(pk: int, user) -> PersonalBookEntry | None:
    return PersonalBookEntry.objects.select_related("book").filter(pk=pk, user=user).first()


def list_clubs(user):
    return list(
        BookClub.objects.filter(memberships__user=user)
        .prefetch_related("memberships__user")
        .order_by("name")
        .distinct()
    )


def get_club(pk: int, user=None) -> BookClub | None:
    qs = BookClub.objects.prefetch_related("memberships__user")
    if user is not None:
        qs = qs.filter(memberships__user=user)
    return qs.filter(pk=pk).first()


def list_club_books(club: BookClub, user=None, *, status: str | None = None):
    qs = (
        BookClubBook.objects.select_related("book", "added_by", "club")
        .filter(club=club)
        .annotate(average_rating=Avg("book__ratings__rating"))
        .order_by("status", "position", "created_at")
    )
    if status:
        qs = qs.filter(status=status)
    entries = list(qs)
    member_ids = list(club.memberships.values_list("user_id", flat=True))
    ratings = list(
        BookRating.objects.select_related("user")
        .filter(book_id__in=[e.book_id for e in entries], user_id__in=member_ids)
        .order_by("user__display_name")
    )
    ratings_by_book: dict[int, list[BookRating]] = {}
    for rating in ratings:
        ratings_by_book.setdefault(rating.book_id, []).append(rating)
    my_ratings = {}
    if user is not None:
        my_ratings = {r.book_id: r.rating for r in BookRating.objects.filter(user=user, book_id__in=[e.book_id for e in entries])}
    for entry in entries:
        entry.ratings = ratings_by_book.get(entry.book_id, [])
        entry.my_rating = my_ratings.get(entry.book_id)
    return entries


def get_club_book(pk: int, club: BookClub | None = None) -> BookClubBook | None:
    qs = BookClubBook.objects.select_related("book", "club", "added_by")
    if club is not None:
        qs = qs.filter(club=club)
    return qs.filter(pk=pk).first()


def list_queue_items(club: BookClub, user=None):
    qs = BookClubQueueItem.objects.select_related("club_book__book", "club_book__club", "club_book__added_by", "club").filter(club=club).order_by("position", "created_at")
    items = list(qs)
    entries = [item.club_book for item in items]
    member_ids = list(club.memberships.values_list("user_id", flat=True))
    ratings = list(BookRating.objects.select_related("user").filter(book_id__in=[e.book_id for e in entries], user_id__in=member_ids))
    ratings_by_book: dict[int, list[BookRating]] = {}
    for rating in ratings:
        ratings_by_book.setdefault(rating.book_id, []).append(rating)
    for entry in entries:
        entry.ratings = ratings_by_book.get(entry.book_id, [])
        entry.average_rating = None
        vals = [r.rating for r in entry.ratings if r.rating is not None]
        if vals:
            entry.average_rating = sum(vals) / len(vals)
        entry.my_rating = None
        if user is not None:
            mine = next((r for r in entry.ratings if r.user_id == user.id), None)
            entry.my_rating = mine.rating if mine else None
    return items


def get_queue_item(pk: int, club: BookClub | None = None) -> BookClubQueueItem | None:
    qs = BookClubQueueItem.objects.select_related("club_book__book", "club_book__club", "club")
    if club is not None:
        qs = qs.filter(club=club)
    return qs.filter(pk=pk).first()
