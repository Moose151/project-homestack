"""Books node models.

Personal shelves and book-club shelves point at the same Book records. Ratings and notes
belong to a user+book pair so a user's rating is shared between their own history and any
club history for the same book.
"""
from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import AllObjectsManager, HouseholdBaseModel, HouseholdManager


class Book(HouseholdBaseModel):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255, blank=True, default="")
    pages = models.PositiveIntegerField(null=True, blank=True)
    genre = models.CharField(max_length=120, blank=True, default="")
    isbn = models.CharField(max_length=32, blank=True, default="")
    description = models.TextField(blank=True, default="")
    cover_url = models.URLField(blank=True, default="")

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["title", "author"]
        indexes = [
            models.Index(fields=["title", "author"]),
            models.Index(fields=["isbn"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} — {self.author}" if self.author else self.title


class BookRating(HouseholdBaseModel):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="ratings")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="book_ratings")
    rating = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    notes = models.TextField(blank=True, default="")

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        unique_together = [("book", "user")]
        ordering = ["book__title"]

    def __str__(self) -> str:
        return f"{self.user_id} rated {self.book_id}: {self.rating}"


class PersonalBookEntry(HouseholdBaseModel):
    class Status(models.TextChoices):
        BACKLOG = "backlog", "Want to Read"
        READING = "reading", "Reading"
        HISTORY = "history", "Read"

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="personal_entries")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="personal_books")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.BACKLOG)
    position = models.PositiveIntegerField(default=0)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        unique_together = [("book", "user")]
        ordering = ["status", "position", "created_at"]

    def __str__(self) -> str:
        return f"{self.user_id}: {self.book} ({self.status})"


class BookClub(HouseholdBaseModel):
    name = models.CharField(max_length=255)
    colour = models.CharField(max_length=20, default="#8B5CF6")
    description = models.TextField(blank=True, default="")
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="BookClubMembership",
        through_fields=("club", "user"),
        related_name="book_clubs",
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class BookClubMembership(HouseholdBaseModel):
    club = models.ForeignKey(BookClub, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="book_club_memberships")

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        unique_together = [("club", "user")]
        ordering = ["user__display_name"]

    def __str__(self) -> str:
        return f"{self.user_id} in {self.club_id}"


class BookClubBook(HouseholdBaseModel):
    class Status(models.TextChoices):
        BACKLOG = "backlog", "Backlog"
        READING = "reading", "Reading"
        HISTORY = "history", "History"

    club = models.ForeignKey(BookClub, on_delete=models.CASCADE, related_name="club_books")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="club_entries")
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.BACKLOG)
    position = models.PositiveIntegerField(default=0)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        unique_together = [("club", "book")]
        ordering = ["status", "position", "created_at"]

    def __str__(self) -> str:
        return f"{self.club}: {self.book} ({self.status})"


class BookClubQueueItem(HouseholdBaseModel):
    club = models.ForeignKey(BookClub, on_delete=models.CASCADE, related_name="queue_items")
    club_book = models.ForeignKey(BookClubBook, on_delete=models.CASCADE, related_name="queue_items")
    position = models.PositiveIntegerField(default=0)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        unique_together = [("club", "club_book")]
        ordering = ["position", "created_at"]

    def __str__(self) -> str:
        return f"{self.club_id} queue {self.club_book_id}"
