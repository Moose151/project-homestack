"""notifications views — thin, self-service (a user only ever sees/acts on their own).

Marking read is self-service on the caller's own rows, so it resolves as the `view` action
rather than a content write.
"""
from __future__ import annotations

from django.conf import settings as django_settings
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications import selectors, services
from apps.notifications.serializers import (
    NotificationPreferenceSerializer,
    NotificationPreferenceWriteSerializer,
    NotificationSerializer,
    PushDeviceRegisterSerializer,
    PushDeviceSerializer,
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


class VapidPublicKeyView(APIView):
    permission_classes = [_Perm]
    permission_action = "view"

    def get(self, request: Request) -> Response:
        return Response({"public_key": django_settings.VAPID_PUBLIC_KEY})


class PushDeviceListView(APIView):
    permission_classes = [_Perm]
    permission_action = "view"

    def get(self, request: Request) -> Response:
        return Response(PushDeviceSerializer(selectors.list_devices(request.user), many=True).data)

    def post(self, request: Request) -> Response:
        serializer = PushDeviceRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        device = services.register_push_device(
            request.user, endpoint=data["endpoint"], p256dh=data["keys"]["p256dh"],
            auth=data["keys"]["auth"], label=data.get("label", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        )
        return Response(PushDeviceSerializer(device).data, status=status.HTTP_201_CREATED)


class PushDeviceDetailView(APIView):
    permission_classes = [_Perm]
    permission_action = "view"

    def delete(self, request: Request, device_id: int) -> Response:
        if not services.unregister_push_device(request.user, device_id):
            raise NotFound()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PushDeviceTestView(APIView):
    permission_classes = [_Perm]
    permission_action = "view"

    def post(self, request: Request, device_id: int) -> Response:
        device = selectors.get_device(request.user, device_id)
        if device is None:
            raise NotFound()
        try:
            delivered = services.send_test_push(device)
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response({"delivered": delivered})
