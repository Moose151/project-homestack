"""
accounts views — thin wrappers that validate input and delegate to services (D10).

Endpoints (API spec §2):
  POST /api/v1/auth/pin-login/
  POST /api/v1/auth/password-login/
  POST /api/v1/auth/logout/
  GET  /api/v1/auth/me/
  POST /api/v1/auth/reauth/
"""
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import services
from apps.accounts.serializers import (
    PasswordLoginSerializer,
    PinLoginSerializer,
    ReauthSerializer,
    UserSerializer,
)


class PinLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request: Request) -> Response:
        serializer = PinLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.pin_login_user(
            request._request,
            serializer.validated_data["username"],
            serializer.validated_data["pin"],
        )
        if user is None:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(UserSerializer(user).data)


class PasswordLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request: Request) -> Response:
        serializer = PasswordLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.password_login_user(
            request._request,
            serializer.validated_data["username"],
            serializer.validated_data["password"],
        )
        if user is None:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    def post(self, request: Request) -> Response:
        services.logout_user(request._request)
        return Response({"detail": "Logged out."})


@method_decorator(ensure_csrf_cookie, name="get")
class MeView(APIView):
    # ensure_csrf_cookie: the web client calls /auth/me/ on load, so this seeds the
    # csrftoken cookie the SPA needs to make authenticated writes (DRF SessionAuth CSRF).
    def get(self, request: Request) -> Response:
        if not request.user.is_authenticated:
            return Response({"detail": "Not authenticated."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(UserSerializer(request.user).data)


@method_decorator(ensure_csrf_cookie, name="get")
class KioskUsersView(APIView):
    """Return household members who can log in via kiosk PIN.

    No authentication required — kiosk avatar selection happens before login.
    Returns only Person records with a linked_user, for display on the kiosk screen.
    Home LAN security model: usernames are not sensitive.

    ensure_csrf_cookie: the kiosk loads this before login, seeding the csrftoken cookie
    so post-login writes (e.g. completing a task) carry a valid CSRF token.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request) -> Response:
        from apps.people.models import Person
        persons = (
            Person.objects.filter(linked_user__isnull=False, linked_user__is_active=True)
            .select_related("linked_user")
            .order_by("display_name")
        )
        data = [
            {
                "person_id": p.pk,
                "display_name": p.display_name,
                "preferred_name": p.preferred_name or p.display_name,
                "avatar": p.avatar,
                "colour": p.colour,
                "profile_type": p.profile_type,
                "username": p.linked_user.username,
            }
            for p in persons
        ]
        return Response(data)


class ReauthView(APIView):
    def post(self, request: Request) -> Response:
        if not request.user.is_authenticated:
            return Response({"detail": "Not authenticated."}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = ReauthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ok = services.reauth_user(request._request, serializer.validated_data["password"])
        if not ok:
            return Response({"detail": "Invalid password."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({"detail": "Re-authentication successful."})
