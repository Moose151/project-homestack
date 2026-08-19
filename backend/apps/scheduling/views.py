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


def _externally_managed_detail(event, verb: str) -> str:
    """Say *which* owner refused the write, so the client can point somewhere useful."""
    if event.is_source_managed:
        return f"Calendar-source entries can only be {verb} through their calendar source."
    return f"Synced events can only be {verb} via their source record."


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
            agenda_only=params.get("agenda") == "1",
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
        event = selectors.get_event(event_id, request.user)
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
        if event.is_externally_managed:
            return Response(
                {"detail": _externally_managed_detail(event, "updated")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = CalendarEventWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        event = services.update_event(request.user, event, **serializer.validated_data)
        return Response(CalendarEventSerializer(event).data)

    def delete(self, request: Request, event_id: int) -> Response:
        event = self._get_event(request, event_id)
        if event.is_externally_managed:
            return Response(
                {"detail": _externally_managed_detail(event, "deleted")},
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


class CalendarSourceListView(APIView):
    """Household calendar sources.

    Viewing is ordinary calendar access; adding, changing or removing a household-wide source
    is a management action, so it resolves `scheduling.manage` rather than being hidden in the
    UI only. Enforcement lives here, not in the frontend.
    """

    # No custom action mapping: the default GET->view / POST->create is already the policy we
    # want, because scheduling.create is seeded to admin and manager only while scheduling.view
    # is granted to everyone. Inventing a `manage` action would mean a permission code nothing
    # grants, and every request would 403.
    permission_classes = [_CalendarPerm]

    def get(self, request: Request) -> Response:
        from apps.scheduling.models import CalendarSource
        from apps.scheduling.serializers import CalendarSourceSerializer
        from apps.scheduling.sources.registry import catalogue

        sources = CalendarSource.objects.all()
        return Response({
            "sources": CalendarSourceSerializer(sources, many=True).data,
            "catalogue": catalogue(),
        })

    def post(self, request: Request) -> Response:
        from apps.scheduling.serializers import (
            CalendarSourceSerializer,
            CalendarSourceWriteSerializer,
        )
        from apps.scheduling.sources.fetching import CalendarFetchError
        from apps.scheduling.sources.ics import IcsParseError

        serializer = CalendarSourceWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            source = services.create_calendar_source(request.user, **serializer.validated_data)
        except (CalendarFetchError, IcsParseError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CalendarSourceSerializer(source).data, status=status.HTTP_201_CREATED)


class CalendarSourceDetailView(APIView):
    # PATCH -> scheduling.edit, DELETE -> scheduling.delete; both admin/manager only.
    permission_classes = [_CalendarPerm]

    def _get(self, source_id: int):
        from apps.scheduling.models import CalendarSource
        return CalendarSource.objects.filter(pk=source_id).first()

    def patch(self, request: Request, source_id: int) -> Response:
        from apps.scheduling.serializers import (
            CalendarSourceSerializer,
            CalendarSourceWriteSerializer,
        )
        from apps.scheduling.sources.fetching import CalendarFetchError

        source = self._get(source_id)
        if source is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = CalendarSourceWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            source = services.update_calendar_source(request.user, source, **serializer.validated_data)
        except CalendarFetchError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CalendarSourceSerializer(source).data)

    def delete(self, request: Request, source_id: int) -> Response:
        source = self._get(source_id)
        if source is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        services.delete_calendar_source(request.user, source)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CalendarSourceSyncView(APIView):
    """Refresh one source now.

    Deliberately its own endpoint rather than something a Calendar page load triggers: fetching
    an external URL must never happen during ordinary browsing.
    """

    permission_classes = [_CalendarPerm]
    permission_action = "edit"

    def post(self, request: Request, source_id: int) -> Response:
        from apps.scheduling.models import CalendarSource
        from apps.scheduling.serializers import CalendarSourceSerializer
        from apps.scheduling.sources.sync import sync_source

        source = CalendarSource.objects.filter(pk=source_id).first()
        if source is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        result = sync_source(source)
        source.refresh_from_db()
        payload = CalendarSourceSerializer(source).data
        payload["result"] = result
        return Response(payload)


class CalendarSourcePreviewView(APIView):
    """Fetch and summarise a feed without saving anything, so the user can confirm first."""

    permission_classes = [_CalendarPerm]
    permission_action = "create"

    def post(self, request: Request) -> Response:
        from apps.core.models import get_active_household
        from apps.scheduling.sources.feeds import normalise_events
        from apps.scheduling.sources.fetching import CalendarFetchError, fetch_calendar
        from apps.scheduling.sources.ics import IcsParseError
        from apps.solace.bill_schedule import household_timezone

        url = (request.data.get("url") or "").strip()
        text = request.data.get("ics_text") or ""
        try:
            if url:
                text = fetch_calendar(url)
            if not text:
                return Response(
                    {"detail": "Provide a calendar URL or file."}, status=status.HTTP_400_BAD_REQUEST,
                )
            entries = normalise_events(text, household_timezone(get_active_household()))
        except (CalendarFetchError, IcsParseError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        future = [row for row in entries if row["start_at"] and row["start_at"] >= now]
        sample = sorted(entries, key=lambda row: row["start_at"])[:5]
        return Response({
            "event_count": len(entries),
            "future_count": len(future),
            "past_count": len(entries) - len(future),
            "sample": [
                {"title": row["summary"], "start_at": row["start_at"], "all_day": row["all_day"]}
                for row in sample
            ],
        })
