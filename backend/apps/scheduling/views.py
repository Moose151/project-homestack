"""scheduling views — thin wrappers over selectors/services (Coding Standards §6)."""
from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.permissions.drf import HomeStackPermission
from apps.scheduling import selectors, services
from apps.scheduling.serializers import CalendarEventSerializer, CalendarEventWriteSerializer

_CalendarPerm = HomeStackPermission.for_resource("scheduling")


class CalendarEventListView(APIView):
    permission_classes = [_CalendarPerm]

    def get(self, request: Request) -> Response:
        upcoming = request.query_params.get("upcoming") == "1"
        events = selectors.list_events(user=request.user, upcoming_only=upcoming)
        return Response(CalendarEventSerializer(events, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = CalendarEventWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = services.create_event(request.user, **serializer.validated_data)
        return Response(CalendarEventSerializer(event).data, status=status.HTTP_201_CREATED)


class CalendarEventDetailView(APIView):
    permission_classes = [_CalendarPerm]

    def _get_event(self, event_id: int):
        from rest_framework.exceptions import NotFound
        event = selectors.get_event(event_id)
        if event is None:
            raise NotFound()
        return event

    def get(self, request: Request, event_id: int) -> Response:
        event = self._get_event(event_id)
        return Response(CalendarEventSerializer(event).data)

    def patch(self, request: Request, event_id: int) -> Response:
        event = self._get_event(event_id)
        if event.is_synced:
            return Response(
                {"detail": "Synced events can only be updated via their source record."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = CalendarEventWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        event = services.update_event(request.user, event, **serializer.validated_data)
        return Response(CalendarEventSerializer(event).data)

    def delete(self, request: Request, event_id: int) -> Response:
        event = self._get_event(event_id)
        if event.is_synced:
            return Response(
                {"detail": "Synced events can only be deleted via their source record."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        services.delete_event(request.user, event)
        return Response(status=status.HTTP_204_NO_CONTENT)
