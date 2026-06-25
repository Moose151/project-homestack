"""User-management views (admin-only via the `users` resource). Thin over user_services."""
from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import selectors, user_services
from apps.accounts.serializers import UserAdminSerializer, UserWriteSerializer
from apps.accounts.user_services import UserAdminError
from apps.permissions.drf import HomeStackPermission

_Perm = HomeStackPermission.for_resource("users")


def _guard(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except UserAdminError as exc:
        raise ValidationError({"detail": str(exc)})


class UserListView(APIView):
    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        return Response(UserAdminSerializer(selectors.list_users(), many=True).data)

    def post(self, request: Request) -> Response:
        s = UserWriteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = _guard(user_services.create_user_account, request.user, **s.validated_data)
        return Response(UserAdminSerializer(user).data, status=status.HTTP_201_CREATED)


class UserDetailView(APIView):
    permission_classes = [_Perm]

    def _get(self, pk: int):
        obj = selectors.get_user_by_id(pk)
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request: Request, user_id: int) -> Response:
        return Response(UserAdminSerializer(self._get(user_id)).data)

    def patch(self, request: Request, user_id: int) -> Response:
        user = self._get(user_id)
        s = UserWriteSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        user = _guard(user_services.update_user_account, request.user, user, **s.validated_data)
        return Response(UserAdminSerializer(user).data)

    def delete(self, request: Request, user_id: int) -> Response:
        user = self._get(user_id)
        if user.id == request.user.id:
            raise ValidationError({"detail": "You cannot deactivate your own account."})
        user_services.deactivate_user(request.user, user)
        return Response(status=status.HTTP_204_NO_CONTENT)
