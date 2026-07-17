from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.books import selectors, services
from apps.books.models import BookClubBook
from apps.books.serializers import (
    BookClubSerializer,
    BookRatingSerializer,
    BookSerializer,
    ClubBookSerializer,
    ClubBookWriteSerializer,
    PersonalBookEntrySerializer,
    PersonalEntryWriteSerializer,
    QueueItemSerializer,
    QueueItemWriteSerializer,
    RatingWriteSerializer,
)
from apps.permissions.drf import HomeStackPermission

_BooksPerm = HomeStackPermission.for_resource("books")


class BooksUsersView(APIView):
    permission_classes = [_BooksPerm]

    def get(self, request: Request) -> Response:
        users = User.objects.filter(is_active=True).order_by("display_name", "username")
        return Response([
            {
                "id": u.id,
                "display_name": u.display_name,
                "username": u.username,
                "colour": u.colour,
                "avatar": u.avatar,
            }
            for u in users
        ])


class BookListView(APIView):
    permission_classes = [_BooksPerm]

    def get(self, request: Request) -> Response:
        query = (request.query_params.get("q") or "").strip()
        return Response(BookSerializer(selectors.list_books(query), many=True).data)

    def post(self, request: Request) -> Response:
        serializer = BookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_book(request.user, **serializer.validated_data)
        return Response(BookSerializer(obj).data, status=status.HTTP_201_CREATED)


class BookDetailView(APIView):
    permission_classes = [_BooksPerm]

    def _get(self, pk: int):
        obj = selectors.get_book(pk)
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request: Request, book_id: int) -> Response:
        return Response(BookSerializer(self._get(book_id)).data)

    def patch(self, request: Request, book_id: int) -> Response:
        obj = self._get(book_id)
        serializer = BookSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_book(request.user, obj, **serializer.validated_data)
        return Response(BookSerializer(obj).data)

    def delete(self, request: Request, book_id: int) -> Response:
        services.delete_book(request.user, self._get(book_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class RatingView(APIView):
    permission_classes = [_BooksPerm]
    permission_action = "edit"

    def post(self, request: Request) -> Response:
        serializer = RatingWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book = selectors.get_book(serializer.validated_data["book_id"])
        if book is None:
            raise NotFound()
        obj = services.upsert_rating(
            request.user,
            book,
            rating=serializer.validated_data.get("rating"),
            notes=serializer.validated_data.get("notes"),
        )
        return Response(BookRatingSerializer(obj).data)


class PersonalShelfView(APIView):
    permission_classes = [_BooksPerm]

    def get(self, request: Request) -> Response:
        include_clubs = request.query_params.get("include_clubs", "1") != "0"
        data = selectors.list_personal_entries(request.user, include_clubs=include_clubs)
        return Response({
            "personal": PersonalBookEntrySerializer(data["personal"], many=True).data,
            "club": ClubBookSerializer(data["club"], many=True).data,
        })

    def post(self, request: Request) -> Response:
        serializer = PersonalEntryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_personal_entry(request.user, **serializer.validated_data)
        data = selectors.list_personal_entries(request.user, include_clubs=False)["personal"]
        obj = next((e for e in data if e.id == obj.id), obj)
        return Response(PersonalBookEntrySerializer(obj).data, status=status.HTTP_201_CREATED)


class PersonalShelfDetailView(APIView):
    permission_classes = [_BooksPerm]
    permission_action = "edit"

    def _get(self, pk: int, user):
        obj = selectors.get_personal_entry(pk, user)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, entry_id: int) -> Response:
        obj = self._get(entry_id, request.user)
        serializer = PersonalEntryWriteSerializer(data={**request.data, "book_id": obj.book_id}, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_personal_entry(request.user, obj, **serializer.validated_data)
        return Response(PersonalBookEntrySerializer(obj).data)

    def delete(self, request: Request, entry_id: int) -> Response:
        services.delete_personal_entry(request.user, self._get(entry_id, request.user))
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClubListView(APIView):
    permission_classes = [_BooksPerm]

    def get(self, request: Request) -> Response:
        return Response(BookClubSerializer(selectors.list_clubs(request.user), many=True).data)

    def post(self, request: Request) -> Response:
        serializer = BookClubSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_club(request.user, **serializer.validated_data)
        return Response(BookClubSerializer(obj).data, status=status.HTTP_201_CREATED)


class ClubDetailView(APIView):
    permission_classes = [_BooksPerm]
    permission_action = "edit"

    def _get(self, pk: int, user):
        obj = selectors.get_club(pk, user=user)
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request: Request, club_id: int) -> Response:
        return Response(BookClubSerializer(self._get(club_id, request.user)).data)

    def patch(self, request: Request, club_id: int) -> Response:
        club = self._get(club_id, request.user)
        serializer = BookClubSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(BookClubSerializer(services.update_club(request.user, club, **serializer.validated_data)).data)

    def delete(self, request: Request, club_id: int) -> Response:
        services.delete_club(request.user, self._get(club_id, request.user))
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClubMemberView(APIView):
    permission_classes = [_BooksPerm]
    permission_action = "edit"

    def _get_club(self, pk: int, user):
        club = selectors.get_club(pk, user=user)
        if club is None:
            raise NotFound()
        return club

    def post(self, request: Request, club_id: int) -> Response:
        club = self._get_club(club_id, request.user)
        user_id = request.data.get("user_id")
        user = User.objects.filter(pk=user_id, is_active=True).first()
        if user is None:
            raise ValidationError({"user_id": "Choose an active HomeStack user."})
        membership = services.add_club_member(request.user, club, user)
        return Response(BookClubSerializer(selectors.get_club(club.id, user=request.user)).data, status=status.HTTP_201_CREATED)

    def delete(self, request: Request, club_id: int, membership_id: int) -> Response:
        club = self._get_club(club_id, request.user)
        membership = club.memberships.filter(pk=membership_id).first()
        if membership is None:
            raise NotFound()
        services.remove_club_member(request.user, membership)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClubBookListView(APIView):
    permission_classes = [_BooksPerm]

    def _get_club(self, pk: int, user):
        club = selectors.get_club(pk, user=user)
        if club is None:
            raise NotFound()
        return club

    def get(self, request: Request, club_id: int) -> Response:
        club = self._get_club(club_id, request.user)
        shelf = request.query_params.get("status") or None
        return Response(ClubBookSerializer(selectors.list_club_books(club, request.user, status=shelf), many=True).data)

    def post(self, request: Request, club_id: int) -> Response:
        club = self._get_club(club_id, request.user)
        serializer = ClubBookWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_club_book(request.user, club, **serializer.validated_data)
        obj = selectors.get_club_book(obj.id, club)
        return Response(ClubBookSerializer(obj).data, status=status.HTTP_201_CREATED)


class ClubBookDetailView(APIView):
    permission_classes = [_BooksPerm]
    permission_action = "edit"

    def _get_club(self, pk: int, user):
        club = selectors.get_club(pk, user=user)
        if club is None:
            raise NotFound()
        return club

    def _get(self, club_id: int, book_entry_id: int, user):
        club = self._get_club(club_id, user)
        obj = selectors.get_club_book(book_entry_id, club)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, club_id: int, book_entry_id: int) -> Response:
        obj = self._get(club_id, book_entry_id, request.user)
        data = {k: v for k, v in request.data.items() if k in {"status", "position"}}
        obj = services.update_club_book(request.user, obj, **data)
        club = selectors.get_club(club_id, request.user)
        return Response(ClubBookSerializer(selectors.list_club_books(club, request.user), many=True).data)

    def delete(self, request: Request, club_id: int, book_entry_id: int) -> Response:
        services.delete_club_book(request.user, self._get(club_id, book_entry_id, request.user))
        return Response(status=status.HTTP_204_NO_CONTENT)


class QueueListView(APIView):
    permission_classes = [_BooksPerm]

    def _get_club(self, pk: int, user):
        club = selectors.get_club(pk, user=user)
        if club is None:
            raise NotFound()
        return club

    def get(self, request: Request, club_id: int) -> Response:
        club = self._get_club(club_id, request.user)
        return Response(QueueItemSerializer(selectors.list_queue_items(club, request.user), many=True).data)

    def post(self, request: Request, club_id: int) -> Response:
        club = self._get_club(club_id, request.user)
        serializer = QueueItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        club_book = selectors.get_club_book(serializer.validated_data["club_book_id"], club)
        if club_book is None:
            raise NotFound()
        item = services.add_queue_item(
            request.user,
            club,
            club_book,
            position=serializer.validated_data.get("position"),
        )
        return Response(QueueItemSerializer(item).data, status=status.HTTP_201_CREATED)


class QueueDetailView(APIView):
    permission_classes = [_BooksPerm]
    permission_action = "edit"

    def _get_club(self, pk: int, user):
        club = selectors.get_club(pk, user=user)
        if club is None:
            raise NotFound()
        return club

    def _get(self, club_id: int, item_id: int, user):
        club = self._get_club(club_id, user)
        item = selectors.get_queue_item(item_id, club)
        if item is None:
            raise NotFound()
        return item

    def patch(self, request: Request, club_id: int, item_id: int) -> Response:
        item = self._get(club_id, item_id, request.user)
        item = services.update_queue_item(request.user, item, position=request.data.get("position", item.position))
        return Response(QueueItemSerializer(item).data)

    def delete(self, request: Request, club_id: int, item_id: int) -> Response:
        services.delete_queue_item(request.user, self._get(club_id, item_id, request.user))
        return Response(status=status.HTTP_204_NO_CONTENT)
