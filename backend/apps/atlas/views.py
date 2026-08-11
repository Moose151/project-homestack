"""atlas views — thin wrappers over selectors/services (Coding Standards §6)."""
from __future__ import annotations

from datetime import date, timedelta

from django.utils.dateparse import parse_date

from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.atlas import selectors, services
from apps.atlas.serializers import (
    AtlasListItemSerializer,
    AtlasContactSerializer,
    AtlasListItemWriteSerializer,
    AtlasListSerializer,
    AtlasListSuggestionSerializer,
    AtlasListWriteSerializer,
    AtlasNoteSerializer,
    AtlasReminderSerializer,
)
from apps.permissions.drf import HomeStackPermission

_AtlasPerm = HomeStackPermission.for_resource("atlas")


class ContactListView(APIView):
    permission_classes = [_AtlasPerm]

    def get(self, request: Request) -> Response:
        return Response(AtlasContactSerializer(selectors.list_contacts(request.user), many=True).data)

    def post(self, request: Request) -> Response:
        serializer = AtlasContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = services.create_contact(request.user, **serializer.validated_data)
        return Response(AtlasContactSerializer(contact).data, status=status.HTTP_201_CREATED)


class ContactDetailView(APIView):
    permission_classes = [_AtlasPerm]

    def _get(self, request, contact_id):
        contact = selectors.get_contact(contact_id, request.user)
        if contact is None:
            raise NotFound()
        return contact

    def get(self, request: Request, contact_id: int) -> Response:
        return Response(AtlasContactSerializer(self._get(request, contact_id)).data)

    def patch(self, request: Request, contact_id: int) -> Response:
        contact = self._get(request, contact_id)
        serializer = AtlasContactSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(AtlasContactSerializer(services.update_contact(request.user, contact, **serializer.validated_data)).data)

    def delete(self, request: Request, contact_id: int) -> Response:
        services.delete_contact(request.user, self._get(request, contact_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


def _birthday_in_year(born: date, year: int) -> date:
    try:
        return born.replace(year=year)
    except ValueError:  # 29 February follows the documented 28 February policy.
        return date(year, 2, 28)


class BirthdayOccurrenceView(APIView):
    permission_classes = [_AtlasPerm]

    def get(self, request: Request) -> Response:
        start = parse_date(request.query_params.get("start") or "") or date.today()
        end = parse_date(request.query_params.get("end") or "") or (start + timedelta(days=366))
        if end <= start or (end - start).days > 732:
            raise ValidationError("Choose an end date after start, within two years.")
        from apps.people.selectors import list_people
        sources = [
            (f"person-{person.id}", person.name, person.date_of_birth, person.id, None)
            for person in list_people(request.user) if person.date_of_birth
        ]
        sources += [
            (f"contact-{contact.id}", contact.name, contact.date_of_birth, None, contact.id)
            for contact in selectors.list_contacts(request.user) if not contact.linked_person_id
        ]
        rows = []
        for source_id, name, born, person_id, contact_id in sources:
            for year in range(start.year, end.year + 1):
                occurrence = _birthday_in_year(born, year)
                if start <= occurrence < end:
                    age = year - born.year
                    rows.append({
                        "id": f"birthday-{source_id}-{year}", "date": occurrence.isoformat(),
                        "title": f"{name} turns {age}", "name": name, "age": age,
                        "person_id": person_id, "contact_id": contact_id, "event_kind": "birthday",
                    })
        return Response(sorted(rows, key=lambda row: (row["date"], row["name"])))


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class AtlasSearchView(APIView):
    """GET /atlas/search/?q= — permission-filtered FTS across notes/lists/items/reminders (D9)."""

    permission_classes = [_AtlasPerm]

    def get(self, request: Request) -> Response:
        query = (request.query_params.get("q") or "").strip()
        if not query:
            return Response({"notes": [], "lists": [], "items": [], "reminders": []})
        results = selectors.search_atlas(request.user, query)
        return Response({
            "notes": AtlasNoteSerializer(results["notes"], many=True).data,
            "lists": AtlasListSerializer(results["lists"], many=True).data,
            "items": AtlasListItemSerializer(results["items"], many=True).data,
            "reminders": AtlasReminderSerializer(results["reminders"], many=True).data,
        })


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

class NoteListView(APIView):
    permission_classes = [_AtlasPerm]

    def get(self, request: Request) -> Response:
        query = request.query_params.get("search")
        if query:
            notes = selectors.search_notes(request.user, query)
        else:
            notes = selectors.list_notes(request.user)
        return Response(AtlasNoteSerializer(notes, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = AtlasNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = services.create_note(request.user, **serializer.validated_data)
        return Response(AtlasNoteSerializer(note).data, status=status.HTTP_201_CREATED)


class NoteDetailView(APIView):
    permission_classes = [_AtlasPerm]

    def _get(self, pk: int):
        note = selectors.get_note(pk)
        if note is None:
            raise NotFound()
        return note

    def get(self, request: Request, note_id: int) -> Response:
        return Response(AtlasNoteSerializer(self._get(note_id)).data)

    def patch(self, request: Request, note_id: int) -> Response:
        note = self._get(note_id)
        serializer = AtlasNoteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        note = services.update_note(request.user, note, **serializer.validated_data)
        return Response(AtlasNoteSerializer(note).data)

    def delete(self, request: Request, note_id: int) -> Response:
        services.delete_note(request.user, self._get(note_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Lists
# ---------------------------------------------------------------------------

class ListListView(APIView):
    permission_classes = [_AtlasPerm]

    def get(self, request: Request) -> Response:
        return Response(AtlasListSerializer(
            selectors.list_atlas_lists(request.user), many=True
        ).data)

    def post(self, request: Request) -> Response:
        serializer = AtlasListWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            atlas_list = services.create_atlas_list(request.user, **serializer.validated_data)
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(AtlasListSerializer(atlas_list).data, status=status.HTTP_201_CREATED)


class ListDetailView(APIView):
    permission_classes = [_AtlasPerm]

    def _get(self, request: Request, pk: int):
        obj = selectors.get_atlas_list(pk, request.user)
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request: Request, list_id: int) -> Response:
        return Response(AtlasListSerializer(self._get(request, list_id)).data)

    def patch(self, request: Request, list_id: int) -> Response:
        atlas_list = self._get(request, list_id)
        if not services.can_manage_personal_list(request.user, atlas_list):
            raise PermissionDenied("Suggest items from their Corner instead of editing this personal list.")
        serializer = AtlasListWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            atlas_list = services.update_atlas_list(request.user, atlas_list, **serializer.validated_data)
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(AtlasListSerializer(atlas_list).data)

    def delete(self, request: Request, list_id: int) -> Response:
        atlas_list = self._get(request, list_id)
        if not services.can_manage_personal_list(request.user, atlas_list):
            raise PermissionDenied("Only the list owner or a household manager can delete this list.")
        services.delete_atlas_list(request.user, atlas_list)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# List items
# ---------------------------------------------------------------------------

class ListItemListView(APIView):
    permission_classes = [_AtlasPerm]

    def _get_list(self, request: Request, list_id: int):
        obj = selectors.get_atlas_list(list_id, request.user)
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request: Request, list_id: int) -> Response:
        atlas_list = self._get_list(request, list_id)
        items = selectors.list_items_for_list(atlas_list)
        return Response(AtlasListItemSerializer(items, many=True).data)

    def post(self, request: Request, list_id: int) -> Response:
        atlas_list = self._get_list(request, list_id)
        if not services.can_manage_personal_list(request.user, atlas_list):
            raise PermissionDenied("Suggest items from their Corner instead of editing this personal list.")
        serializer = AtlasListItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = services.create_list_item(request.user, atlas_list, **serializer.validated_data)
        return Response(AtlasListItemSerializer(item).data, status=status.HTTP_201_CREATED)


class ListItemDetailView(APIView):
    permission_classes = [_AtlasPerm]

    def _get_item(self, request: Request, list_id: int, item_id: int):
        atlas_list = selectors.get_atlas_list(list_id, request.user)
        if atlas_list is None:
            raise NotFound()
        item = selectors.get_list_item(item_id)
        if item is None or item.atlas_list_id != list_id:
            raise NotFound()
        return item

    def patch(self, request: Request, list_id: int, item_id: int) -> Response:
        item = self._get_item(request, list_id, item_id)
        if not services.can_manage_personal_list(request.user, item.atlas_list):
            raise PermissionDenied("Suggest items from their Corner instead of editing this personal list.")
        serializer = AtlasListItemWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        item = services.update_list_item(request.user, item, **serializer.validated_data)
        return Response(AtlasListItemSerializer(item).data)

    def delete(self, request: Request, list_id: int, item_id: int) -> Response:
        item = self._get_item(request, list_id, item_id)
        if not services.can_manage_personal_list(request.user, item.atlas_list):
            raise PermissionDenied("Only the list owner or a household manager can delete this item.")
        services.delete_list_item(request.user, item)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ListItemCompleteView(APIView):
    permission_classes = [_AtlasPerm]
    permission_action = "edit"

    def post(self, request: Request, list_id: int, item_id: int) -> Response:
        atlas_list = selectors.get_atlas_list(list_id, request.user)
        if atlas_list is None:
            raise NotFound()
        if not services.can_manage_personal_list(request.user, atlas_list):
            raise PermissionDenied("Only the list owner can complete this item.")
        item = selectors.get_list_item(item_id)
        if item is None or item.atlas_list_id != list_id:
            raise NotFound()
        item = services.complete_list_item(request.user, item)
        return Response(AtlasListItemSerializer(item).data)


class ListItemUncompleteView(APIView):
    permission_classes = [_AtlasPerm]
    permission_action = "edit"

    def post(self, request: Request, list_id: int, item_id: int) -> Response:
        atlas_list = selectors.get_atlas_list(list_id, request.user)
        if atlas_list is None:
            raise NotFound()
        if not services.can_manage_personal_list(request.user, atlas_list):
            raise PermissionDenied("Only the list owner can reopen this item.")
        item = selectors.get_list_item(item_id)
        if item is None or item.atlas_list_id != list_id:
            raise NotFound()
        item = services.uncomplete_list_item(request.user, item)
        return Response(AtlasListItemSerializer(item).data)


class ListSuggestionListView(APIView):
    permission_classes = [_AtlasPerm]

    def _list(self, request: Request, list_id: int):
        obj = selectors.get_atlas_list(list_id, request.user)
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request: Request, list_id: int) -> Response:
        atlas_list = self._list(request, list_id)
        if not services.can_manage_personal_list(request.user, atlas_list):
            raise PermissionDenied("Only the list owner or a household manager can review suggestions.")
        return Response(AtlasListSuggestionSerializer(
            selectors.list_suggestions(atlas_list), many=True
        ).data)

    def post(self, request: Request, list_id: int) -> Response:
        serializer = AtlasListSuggestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            row = services.create_list_suggestion(
                request.user, self._list(request, list_id), **serializer.validated_data
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(AtlasListSuggestionSerializer(row).data, status=status.HTTP_201_CREATED)


class ListSuggestionReviewView(APIView):
    permission_classes = [_AtlasPerm]
    permission_action = "edit"

    def post(self, request: Request, list_id: int, suggestion_id: int, action: str) -> Response:
        atlas_list = selectors.get_atlas_list(list_id, request.user)
        if atlas_list is None:
            raise NotFound()
        suggestion = selectors.get_suggestion(atlas_list, suggestion_id)
        if suggestion is None:
            raise NotFound()
        try:
            if action == "accept":
                suggestion = services.accept_list_suggestion(request.user, suggestion)
            elif action == "dismiss":
                suggestion = services.dismiss_list_suggestion(request.user, suggestion)
            else:
                raise NotFound()
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(AtlasListSuggestionSerializer(suggestion).data)


# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------

class ReminderListView(APIView):
    permission_classes = [_AtlasPerm]

    def get(self, request: Request) -> Response:
        upcoming = request.query_params.get("upcoming") == "1"
        reminders = selectors.list_reminders(request.user, upcoming_only=upcoming)
        return Response(AtlasReminderSerializer(reminders, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = AtlasReminderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reminder = services.create_reminder(request.user, **serializer.validated_data)
        return Response(AtlasReminderSerializer(reminder).data, status=status.HTTP_201_CREATED)


class ReminderDetailView(APIView):
    permission_classes = [_AtlasPerm]

    def _get(self, pk: int):
        obj = selectors.get_reminder(pk)
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request: Request, reminder_id: int) -> Response:
        return Response(AtlasReminderSerializer(self._get(reminder_id)).data)

    def patch(self, request: Request, reminder_id: int) -> Response:
        reminder = self._get(reminder_id)
        serializer = AtlasReminderSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        reminder = services.update_reminder(request.user, reminder, **serializer.validated_data)
        return Response(AtlasReminderSerializer(reminder).data)

    def delete(self, request: Request, reminder_id: int) -> Response:
        services.delete_reminder(request.user, self._get(reminder_id))
        return Response(status=status.HTTP_204_NO_CONTENT)
