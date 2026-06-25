"""atlas views — thin wrappers over selectors/services (Coding Standards §6)."""
from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.atlas import selectors, services
from apps.atlas.serializers import (
    AtlasListItemSerializer,
    AtlasListItemWriteSerializer,
    AtlasListSerializer,
    AtlasListWriteSerializer,
    AtlasNoteSerializer,
    AtlasReminderSerializer,
)
from apps.permissions.drf import HomeStackPermission

_AtlasPerm = HomeStackPermission.for_resource("atlas")


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
        atlas_list = services.create_atlas_list(request.user, **serializer.validated_data)
        return Response(AtlasListSerializer(atlas_list).data, status=status.HTTP_201_CREATED)


class ListDetailView(APIView):
    permission_classes = [_AtlasPerm]

    def _get(self, pk: int):
        obj = selectors.get_atlas_list(pk)
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request: Request, list_id: int) -> Response:
        return Response(AtlasListSerializer(self._get(list_id)).data)

    def patch(self, request: Request, list_id: int) -> Response:
        atlas_list = self._get(list_id)
        serializer = AtlasListWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        atlas_list = services.update_atlas_list(request.user, atlas_list, **serializer.validated_data)
        return Response(AtlasListSerializer(atlas_list).data)

    def delete(self, request: Request, list_id: int) -> Response:
        services.delete_atlas_list(request.user, self._get(list_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# List items
# ---------------------------------------------------------------------------

class ListItemListView(APIView):
    permission_classes = [_AtlasPerm]

    def _get_list(self, list_id: int):
        obj = selectors.get_atlas_list(list_id)
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request: Request, list_id: int) -> Response:
        atlas_list = self._get_list(list_id)
        items = selectors.list_items_for_list(atlas_list)
        return Response(AtlasListItemSerializer(items, many=True).data)

    def post(self, request: Request, list_id: int) -> Response:
        atlas_list = self._get_list(list_id)
        serializer = AtlasListItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = services.create_list_item(request.user, atlas_list, **serializer.validated_data)
        return Response(AtlasListItemSerializer(item).data, status=status.HTTP_201_CREATED)


class ListItemDetailView(APIView):
    permission_classes = [_AtlasPerm]

    def _get_item(self, list_id: int, item_id: int):
        item = selectors.get_list_item(item_id)
        if item is None or item.atlas_list_id != list_id:
            raise NotFound()
        return item

    def patch(self, request: Request, list_id: int, item_id: int) -> Response:
        item = self._get_item(list_id, item_id)
        serializer = AtlasListItemWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        item = services.update_list_item(request.user, item, **serializer.validated_data)
        return Response(AtlasListItemSerializer(item).data)

    def delete(self, request: Request, list_id: int, item_id: int) -> Response:
        item = self._get_item(list_id, item_id)
        services.delete_list_item(request.user, item)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ListItemCompleteView(APIView):
    permission_classes = [_AtlasPerm]
    permission_action = "edit"

    def post(self, request: Request, list_id: int, item_id: int) -> Response:
        item = selectors.get_list_item(item_id)
        if item is None or item.atlas_list_id != list_id:
            raise NotFound()
        item = services.complete_list_item(request.user, item)
        return Response(AtlasListItemSerializer(item).data)


class ListItemUncompleteView(APIView):
    permission_classes = [_AtlasPerm]
    permission_action = "edit"

    def post(self, request: Request, list_id: int, item_id: int) -> Response:
        item = selectors.get_list_item(item_id)
        if item is None or item.atlas_list_id != list_id:
            raise NotFound()
        item = services.uncomplete_list_item(request.user, item)
        return Response(AtlasListItemSerializer(item).data)


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
