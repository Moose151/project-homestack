"""scheduling views — thin wrappers over selectors/services (Coding Standards §6)."""
from __future__ import annotations

from datetime import datetime, time

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.permissions.drf import HomeStackPermission
from apps.accounts.services import is_reauthed
from apps.scheduling import selectors, services
from apps.scheduling.serializers import (
    CalendarEventSerializer,
    CalendarEventWriteSerializer,
    RotatingScheduleExceptionSerializer,
    RotatingScheduleExceptionWriteSerializer,
    RotatingScheduleSerializer,
    RotatingScheduleWriteSerializer,
)

_CalendarPerm = HomeStackPermission.for_resource("scheduling")


def _parse_dt(value: str | None):
    """Parse an ISO datetime or date query param into an aware datetime (or None)."""
    if not value:
        return None
    dt = parse_datetime(value)
    if dt is None:
        d = parse_date(value)
        if d is not None:
            dt = datetime.combine(d, time.min)
    if dt is not None and timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt


class CalendarEventListView(APIView):
    permission_classes = [_CalendarPerm]

    def get(self, request: Request) -> Response:
        params = request.query_params
        person = params.get("person")
        events = selectors.list_events(
            user=request.user,
            upcoming_only=params.get("upcoming") == "1",
            start=_parse_dt(params.get("start")),
            end=_parse_dt(params.get("end")),
            node=params.get("node") or None,
            person=int(person) if person and person.isdigit() else None,
            sensitive_unlocked=is_reauthed(request._request),
        )
        return Response(CalendarEventSerializer(events, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = CalendarEventWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = services.create_event(request.user, **serializer.validated_data)
        return Response(CalendarEventSerializer(event).data, status=status.HTTP_201_CREATED)


class CalendarEventDetailView(APIView):
    permission_classes = [_CalendarPerm]

    def _get_event(self, request: Request, event_id: int):
        from rest_framework.exceptions import NotFound
        event = selectors.get_event(event_id)
        if event is None:
            raise NotFound()
        if (
            not is_reauthed(request._request)
            and (event.visibility == "sensitive" or event.sensitivity in {"financial", "health", "document", "private"})
        ):
            raise PermissionDenied("Password re-authentication required for sensitive events.")
        return event

    def get(self, request: Request, event_id: int) -> Response:
        event = self._get_event(request, event_id)
        return Response(CalendarEventSerializer(event).data)

    def patch(self, request: Request, event_id: int) -> Response:
        event = self._get_event(request, event_id)
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
        event = self._get_event(request, event_id)
        if event.is_synced:
            return Response(
                {"detail": "Synced events can only be deleted via their source record."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        services.delete_event(request.user, event)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RotatingScheduleListView(APIView):
    permission_classes = [_CalendarPerm]

    def get(self, request: Request) -> Response:
        schedules = selectors.list_rotating_schedules(request.user)
        return Response(RotatingScheduleSerializer(schedules, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = RotatingScheduleWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        schedule = services.create_rotating_schedule(
            request.user, **serializer.validated_data
        )
        return Response(
            RotatingScheduleSerializer(schedule).data,
            status=status.HTTP_201_CREATED,
        )


class RotatingScheduleDetailView(APIView):
    permission_classes = [_CalendarPerm]

    def _get(self, request: Request, schedule_id: int):
        from rest_framework.exceptions import NotFound

        schedule = selectors.get_rotating_schedule(schedule_id, request.user)
        if schedule is None:
            raise NotFound()
        return schedule

    def get(self, request: Request, schedule_id: int) -> Response:
        return Response(RotatingScheduleSerializer(self._get(request, schedule_id)).data)

    def patch(self, request: Request, schedule_id: int) -> Response:
        schedule = self._get(request, schedule_id)
        serializer = RotatingScheduleWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = services.update_rotating_schedule(
            request.user, schedule, **serializer.validated_data
        )
        return Response(RotatingScheduleSerializer(updated).data)

    def delete(self, request: Request, schedule_id: int) -> Response:
        services.delete_rotating_schedule(request.user, self._get(request, schedule_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class RotatingScheduleOccurrenceListView(APIView):
    permission_classes = [_CalendarPerm]

    def get(self, request: Request) -> Response:
        start = parse_date(request.query_params.get("start", ""))
        end = parse_date(request.query_params.get("end", ""))
        if start is None or end is None:
            return Response(
                {"detail": "start and end must be ISO dates."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if end <= start:
            return Response(
                {"detail": "end must be after start."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if (end - start).days > 400:
            return Response(
                {"detail": "Request no more than 400 days at a time."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            selectors.expand_rotating_schedules(request.user, start=start, end=end)
        )


class RotatingScheduleExceptionDetailView(APIView):
    permission_classes = [_CalendarPerm]

    def _values(self, request: Request, schedule_id: int, date: str):
        from rest_framework.exceptions import NotFound, ValidationError

        schedule = selectors.get_rotating_schedule(schedule_id, request.user)
        if schedule is None:
            raise NotFound()
        parsed_date = parse_date(date)
        if parsed_date is None:
            raise ValidationError({"date": "Use an ISO date."})
        return schedule, parsed_date

    def put(self, request: Request, schedule_id: int, date: str) -> Response:
        schedule, parsed_date = self._values(request, schedule_id, date)
        serializer = RotatingScheduleExceptionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        exception = services.set_rotating_schedule_exception(
            request.user,
            schedule,
            parsed_date,
            **serializer.validated_data,
        )
        return Response(RotatingScheduleExceptionSerializer(exception).data)

    def delete(self, request: Request, schedule_id: int, date: str) -> Response:
        schedule, parsed_date = self._values(request, schedule_id, date)
        services.delete_rotating_schedule_exception(
            request.user, schedule, parsed_date
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
