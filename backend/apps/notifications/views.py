"""notifications views — thin, self-service (a user only ever sees/acts on their own).

Marking read is self-service on the caller's own rows, so it resolves as the `view` action
rather than a content write.
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications import selectors, services
from apps.notifications.serializers import (
    NotificationPreferenceSerializer,
    NotificationPreferenceWriteSerializer,
    NotificationSerializer,
    UserNotificationSettingsSerializer,
)
from apps.permissions.drf import HomeStackPermission

_Perm = HomeStackPermission.for_resource("notifications")


class NotificationListView(APIView):
    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        notes = selectors.list_for_user(
            request.user, unread_only=request.query_params.get("unread") == "1"
        )
        return Response({
            "unread_count": selectors.unread_count(request.user),
            "results": NotificationSerializer(notes, many=True).data,
        })


class NotificationReadView(APIView):
    permission_classes = [_Perm]
    permission_action = "view"  # self-service on own row

    def post(self, request: Request, notification_id: int) -> Response:
        note = selectors.get_for_user(request.user, notification_id)
        if note is None:
            raise NotFound()
        return Response(NotificationSerializer(services.mark_read(note)).data)


class NotificationReadAllView(APIView):
    permission_classes = [_Perm]
    permission_action = "view"

    def post(self, request: Request) -> Response:
        count = services.mark_all_read(request.user)
        return Response({"marked_read": count}, status=status.HTTP_200_OK)


class NotificationPreferenceListView(APIView):
    """Self-service: a user only ever reads/writes their own preferences."""

    permission_classes = [_Perm]
    permission_action = "view"

    def get(self, request: Request) -> Response:
        rows = selectors.list_preferences_for_user(request.user)
        return Response(NotificationPreferenceSerializer(rows, many=True).data)

    def patch(self, request: Request) -> Response:
        serializer = NotificationPreferenceWriteSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        services.set_preferences(request.user, serializer.validated_data)
        return Response(NotificationPreferenceSerializer(
            selectors.list_preferences_for_user(request.user), many=True,
        ).data)


class NotificationSettingsView(APIView):
    permission_classes = [_Perm]
    permission_action = "view"

    def get(self, request: Request) -> Response:
        return Response(
            UserNotificationSettingsSerializer(services.get_or_create_settings(request.user)).data
        )

    def patch(self, request: Request) -> Response:
        serializer = UserNotificationSettingsSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_settings(request.user, **serializer.validated_data)
        return Response(UserNotificationSettingsSerializer(obj).data)
