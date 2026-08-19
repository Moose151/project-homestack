"""atlas views — thin wrappers over selectors/services (Coding Standards §6)."""
from __future__ import annotations

from datetime import date, timedelta

from django.utils.dateparse import parse_date

from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError
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


def _ordinal(n: int) -> str:
    if 11 <= n % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class BirthdayOccurrenceView(APIView):
    """Virtual, computed-on-read annual birthdays — People, external Contacts, and Pets.

    Nothing here is persisted as a CalendarEvent (D19 §N reuses the existing People mechanism
    rather than building a second one): every occurrence is derived fresh from date_of_birth on
    every request, so changing/clearing a DOB just changes what the next request returns.
    """

    permission_classes = [_AtlasPerm]

    def get(self, request: Request) -> Response:
        start = parse_date(request.query_params.get("start") or "") or date.today()
        end = parse_date(request.query_params.get("end") or "") or (start + timedelta(days=366))
        if end <= start or (end - start).days > 732:
            raise ValidationError("Choose an end date after start, within two years.")
        from apps.people.selectors import list_people
        from apps.pets.selectors import list_pets
        sources = [
            (f"person-{person.id}", person.name, person.date_of_birth, {"person_id": person.id})
            for person in list_people(request.user) if person.date_of_birth
        ]
        sources += [
            (f"contact-{contact.id}", contact.name, contact.date_of_birth, {"contact_id": contact.id})
            for contact in selectors.list_contacts(request.user) if not contact.linked_person_id
        ]
        dated_pets = [pet for pet in list_pets(request.user) if pet.date_of_birth]
        pet_source_ids = {f"pet-{pet.id}" for pet in dated_pets}
        sources += [
            (f"pet-{pet.id}", pet.name, pet.date_of_birth, {"pet_id": pet.id})
            for pet in dated_pets
        ]
        rows = []
        for source_id, name, born, ref in sources:
            for year in range(start.year, end.year + 1):
                occurrence = _birthday_in_year(born, year)
                if start <= occurrence < end:
                    age = year - born.year
                    title = f"{name}'s {_ordinal(age)} Birthday" if source_id in pet_source_ids else f"{name} turns {age}"
                    rows.append({
                        "id": f"birthday-{source_id}-{year}", "date": occurrence.isoformat(),
                        "title": title, "name": name, "age": age,
                        "person_id": ref.get("person_id"), "contact_id": ref.get("contact_id"),
                        "pet_id": ref.get("pet_id"), "event_kind": "birthday",
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
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
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
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
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


def _get_item_or_404(request: Request, list_id: int, item_id: int):
    atlas_list = selectors.get_atlas_list(list_id, request.user)
    if atlas_list is None:
        raise NotFound()
    item = selectors.get_list_item(item_id)
    if item is None or item.atlas_list_id != list_id:
        raise NotFound()
    return item


class ListItemDetailView(APIView):
    permission_classes = [_AtlasPerm]

    def _get_item(self, request: Request, list_id: int, item_id: int):
        return _get_item_or_404(request, list_id, item_id)

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


class ListItemMoveView(APIView):
    """POST .../items/<id>/move/ {destination_list_id} — To-do "Move to" (D19 §D)."""

    permission_classes = [_AtlasPerm]
    permission_action = "edit"

    def post(self, request: Request, list_id: int, item_id: int) -> Response:
        item = _get_item_or_404(request, list_id, item_id)
        if not services.can_manage_personal_list(request.user, item.atlas_list):
            raise PermissionDenied("Suggest items from their Corner instead of editing this personal list.")
        destination_id = request.data.get("destination_list_id")
        destination = selectors.get_atlas_list(destination_id, request.user) if destination_id else None
        if destination is None:
            raise NotFound("Destination list not found.")
        if not services.can_manage_personal_list(request.user, destination):
            raise PermissionDenied("Cannot move an item into a personal list you cannot edit.")
        try:
            item = services.move_list_item(request.user, item, destination)
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(AtlasListItemSerializer(item).data)


# ---------------------------------------------------------------------------
# Grocery — the single household list (D19 §C)
# ---------------------------------------------------------------------------

class GroceryListView(APIView):
    """GET/POST /atlas/grocery/ — the one household Grocery list, created on first use."""

    permission_classes = [_AtlasPerm]

    def get(self, request: Request) -> Response:
        grocery_list = services.ensure_household_grocery_list(request.user)
        return Response(AtlasListSerializer(grocery_list).data)

    def post(self, request: Request) -> Response:
        grocery_list = services.ensure_household_grocery_list(request.user)
        serializer = AtlasListItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        title = serializer.validated_data.get("title", "")
        duplicate = services.find_duplicate_open_item(grocery_list, title)
        if duplicate is not None:
            return Response(AtlasListItemSerializer(duplicate).data)
        item = services.create_list_item(request.user, grocery_list, **serializer.validated_data)
        return Response(AtlasListItemSerializer(item).data, status=status.HTTP_201_CREATED)


class GroceryClearBoughtView(APIView):
    """POST /atlas/grocery/clear-bought/ — permanently remove completed grocery items."""

    permission_classes = [_AtlasPerm]
    permission_action = "edit"

    def post(self, request: Request) -> Response:
        grocery_list = services.ensure_household_grocery_list(request.user)
        cleared = services.clear_completed_items(request.user, grocery_list)
        return Response({"cleared": cleared})


class GrocerySuggestionsView(APIView):
    """GET /atlas/grocery/suggestions/ — frequently-bought item titles (D19 §C)."""

    permission_classes = [_AtlasPerm]

    def get(self, request: Request) -> Response:
        grocery_list = services.ensure_household_grocery_list(request.user)
        return Response(selectors.frequent_grocery_titles(grocery_list))


# ---------------------------------------------------------------------------
# To-dos — Household + one list per active Person (D19 §D)
# ---------------------------------------------------------------------------

class TodoListsView(APIView):
    """GET /atlas/todos/lists/ — Household + every personal To-do list, with items."""

    permission_classes = [_AtlasPerm]

    def get(self, request: Request) -> Response:
        services.ensure_household_todo_list(request.user)
        from apps.people.selectors import list_people
        for person in list_people(request.user):
            services.ensure_person_todo_list(person, request.user)
        lists = selectors.list_todo_lists(request.user)
        return Response(AtlasListSerializer(lists, many=True).data)


class TodoTodayView(APIView):
    """GET /atlas/todos/today/ — overdue + due-today across Household + personal lists."""

    permission_classes = [_AtlasPerm]

    def get(self, request: Request) -> Response:
        return Response(AtlasListItemSerializer(selectors.list_today_items(request.user), many=True).data)


class TodoQuickCreateView(APIView):
    """POST /atlas/todos/quick-create/ — capture a To-do without naming a list (D19 §D/§E).

    The one endpoint behind Calendar's "Reminder" action and the ambient Quick Add. Both used to
    POST an ``AtlasReminder``; routing them here is what stops ordinary user flows from creating
    a second, parallel reminder object alongside the To-do model.
    """

    permission_classes = [_AtlasPerm]
    permission_action = "edit"

    def post(self, request: Request) -> Response:
        serializer = AtlasListItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = services.quick_create_todo(request.user, **serializer.validated_data)
        return Response(AtlasListItemSerializer(item).data, status=status.HTTP_201_CREATED)


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
# Reminders — legacy, read-only (D19 §E)
# ---------------------------------------------------------------------------

class LegacyReminderWriteRemoved(APIException):
    """410 for any attempt to write through the retired Reminder API.

    410 rather than 404 or 405 because the distinction matters to a caller: the resource is not
    missing and the method is not merely unsupported here — this capability existed, was removed
    deliberately, and has a named successor. The message says where to go.
    """

    status_code = status.HTTP_410_GONE
    default_detail = (
        "Atlas reminders were replaced by to-dos in v0.40. A reminder is now a to-do with a due "
        "date and notification offsets — create one with POST /api/v1/atlas/todos/quick-create/. "
        "Existing reminders remain readable here as archival data."
    )
    default_code = "reminder_api_retired"


class ReminderListView(APIView):
    """GET only. Archival reminders stay readable; nothing may create another one.

    Leaving POST open is what would let the parallel Reminder/To-do model this release removed
    be reintroduced by any client — an AtlasReminder and an AtlasListItem are both
    CalendarSyncMixin records swept by different schedulers, so a new reminder means a second
    calendar entry and a second notification for something a to-do already covers.

    The old payload is deliberately *not* forwarded to the to-do endpoint. The two shapes are
    close but not equivalent — ``body`` vs ``notes``, and a boolean ``notifications_enabled``
    vs a list of offsets whose correct translation depends on ``is_all_day`` — so silently
    reinterpreting one as the other would guess at the caller's intent.
    """

    permission_classes = [_AtlasPerm]

    def get(self, request: Request) -> Response:
        upcoming = request.query_params.get("upcoming") == "1"
        reminders = selectors.list_reminders(request.user, upcoming_only=upcoming)
        return Response(AtlasReminderSerializer(reminders, many=True).data)

    def post(self, request: Request) -> Response:
        raise LegacyReminderWriteRemoved()


class ReminderDetailView(APIView):
    """GET only, for the same reason as the list view.

    PATCH and DELETE are closed too: both run the record back through the reminder service,
    which re-syncs (or removes) its CalendarEvent and would put an archival row back into the
    calendar/notification workflows it was retired out of.
    """

    permission_classes = [_AtlasPerm]

    def _get(self, pk: int):
        obj = selectors.get_reminder(pk)
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request: Request, reminder_id: int) -> Response:
        return Response(AtlasReminderSerializer(self._get(reminder_id)).data)

    def patch(self, request: Request, reminder_id: int) -> Response:
        raise LegacyReminderWriteRemoved()

    def delete(self, request: Request, reminder_id: int) -> Response:
        raise LegacyReminderWriteRemoved()
