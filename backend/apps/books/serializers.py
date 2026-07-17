from __future__ import annotations

from rest_framework import serializers

from apps.books.models import Book, BookClub, BookClubBook, BookClubMembership, BookClubQueueItem, BookRating, PersonalBookEntry


def _non_blank(value: str) -> str:
    if not value.strip():
        raise serializers.ValidationError("This field may not be blank.")
    return value


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ["id", "title", "author", "pages", "genre", "isbn", "description", "cover_url", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_title(self, value: str) -> str:
        return _non_blank(value)


class BookRatingSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.display_name", read_only=True, default="")
    user_colour = serializers.CharField(source="user.colour", read_only=True, default="")

    class Meta:
        model = BookRating
        fields = ["id", "book_id", "user_id", "user_name", "user_colour", "rating", "notes", "created_at", "updated_at"]
        read_only_fields = ["id", "user_id", "user_name", "user_colour", "created_at", "updated_at"]


class RatingWriteSerializer(serializers.Serializer):
    book_id = serializers.IntegerField()
    rating = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=10)
    notes = serializers.CharField(required=False, allow_blank=True)


class PersonalBookEntrySerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    book_id = serializers.IntegerField(required=False)
    rating = serializers.IntegerField(source="book_rating.rating", read_only=True, allow_null=True)
    notes = serializers.CharField(source="book_rating.notes", read_only=True, default="")
    source = serializers.SerializerMethodField()

    class Meta:
        model = PersonalBookEntry
        fields = ["id", "book_id", "book", "status", "position", "rating", "notes", "source", "created_at", "updated_at"]
        read_only_fields = ["id", "book", "rating", "notes", "source", "created_at", "updated_at"]

    def get_source(self, _obj) -> str:
        return "personal"


class PersonalEntryWriteSerializer(serializers.Serializer):
    book_id = serializers.IntegerField(required=False)
    book = BookSerializer(required=False)
    status = serializers.ChoiceField(choices=PersonalBookEntry.Status.choices, default=PersonalBookEntry.Status.BACKLOG)
    position = serializers.IntegerField(required=False, min_value=0)

    def validate(self, attrs):
        if not attrs.get("book_id") and not attrs.get("book"):
            raise serializers.ValidationError({"book": "Provide book_id or book details."})
        return attrs


class BookClubMembershipSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.display_name", read_only=True, default="")
    user_colour = serializers.CharField(source="user.colour", read_only=True, default="")
    user_avatar = serializers.CharField(source="user.avatar", read_only=True, default="")

    class Meta:
        model = BookClubMembership
        fields = ["id", "user_id", "user_name", "user_colour", "user_avatar", "created_at"]
        read_only_fields = ["id", "user_name", "user_colour", "user_avatar", "created_at"]


class BookClubSerializer(serializers.ModelSerializer):
    memberships = BookClubMembershipSerializer(many=True, read_only=True)

    class Meta:
        model = BookClub
        fields = ["id", "name", "colour", "description", "memberships", "created_at", "updated_at"]
        read_only_fields = ["id", "memberships", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        return _non_blank(value)


class ClubBookSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    book_id = serializers.IntegerField(required=False)
    added_by_name = serializers.CharField(source="added_by.display_name", read_only=True, default="")
    added_by_colour = serializers.CharField(source="added_by.colour", read_only=True, default="")
    average_rating = serializers.FloatField(read_only=True)
    my_rating = serializers.IntegerField(read_only=True, allow_null=True)
    ratings = BookRatingSerializer(many=True, read_only=True)

    class Meta:
        model = BookClubBook
        fields = [
            "id", "club_id", "book_id", "book", "status", "position",
            "added_by_id", "added_by_name", "added_by_colour",
            "average_rating", "my_rating", "ratings", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "club_id", "book", "added_by_id", "added_by_name", "added_by_colour", "average_rating", "my_rating", "ratings", "created_at", "updated_at"]


class ClubBookWriteSerializer(serializers.Serializer):
    book_id = serializers.IntegerField(required=False)
    book = BookSerializer(required=False)
    status = serializers.ChoiceField(choices=BookClubBook.Status.choices, default=BookClubBook.Status.BACKLOG)
    position = serializers.IntegerField(required=False, min_value=0)

    def validate(self, attrs):
        if not attrs.get("book_id") and not attrs.get("book"):
            raise serializers.ValidationError({"book": "Provide book_id or book details."})
        return attrs


class QueueItemSerializer(serializers.ModelSerializer):
    club_book = ClubBookSerializer(read_only=True)

    class Meta:
        model = BookClubQueueItem
        fields = ["id", "club_id", "club_book_id", "club_book", "position", "created_at", "updated_at"]
        read_only_fields = ["id", "club_id", "club_book", "created_at", "updated_at"]


class QueueItemWriteSerializer(serializers.Serializer):
    club_book_id = serializers.IntegerField()
    position = serializers.IntegerField(required=False, min_value=0)
