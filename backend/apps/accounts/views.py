"""
accounts views — thin wrappers that validate input and delegate to services (D10).

Endpoints (API spec §2):
  POST /api/v1/auth/pin-login/
  POST /api/v1/auth/password-login/
  POST /api/v1/auth/logout/
  GET  /api/v1/auth/me/
  POST /api/v1/auth/reauth/
"""
from django.contrib.auth import update_session_auth_hash
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import services
from apps.accounts.serializers import (
    GuideDismissalSerializer,
    PasswordLoginSerializer,
    PinLoginSerializer,
    ReauthSerializer,
    UserSerializer,
    UserWriteSerializer,
)
from apps.accounts.user_services import update_user_account


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
        services.mark_session_surface(
            request._request, serializer.validated_data.get("surface", "")
        )
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
        services.mark_session_surface(
            request._request, serializer.validated_data.get("surface", "")
        )
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    def post(self, request: Request) -> Response:
        services.logout_user(request._request)
        return Response({"detail": "Logged out."})


@method_decorator(ensure_csrf_cookie, name="get")
class MeView(APIView):
    def get(self, request: Request) -> Response:
        if not request.user.is_authenticated:
            return Response({"detail": "Not authenticated."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(UserSerializer(request.user).data)

    def patch(self, request: Request) -> Response:
        """Let the logged-in user update their own display_name, colour, avatar, pin, password."""
        if not request.user.is_authenticated:
            return Response({"detail": "Not authenticated."}, status=status.HTTP_401_UNAUTHORIZED)
        # Allow only self-editable fields (no role/is_child/is_active changes via self-edit)
        _SELF_FIELDS = {"display_name", "colour", "avatar", "pin", "password"}
        filtered = {k: v for k, v in request.data.items() if k in _SELF_FIELDS}
        serializer = UserWriteSerializer(data=filtered, partial=True)
        serializer.is_valid(raise_exception=True)
        user = update_user_account(request.user, request.user, **serializer.validated_data)
        if serializer.validated_data.get("password"):
            update_session_auth_hash(request._request, user)
        return Response(UserSerializer(user).data)


class KioskUsersView(APIView):
    """Return household members who can log in via kiosk PIN.

    No authentication required — kiosk avatar selection happens before login.
    Returns only Person records with a linked_user, for display on the kiosk screen.
    Home LAN security model: usernames are not sensitive.
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
                # The account picture (emoji or image) lives on the login User; fall back
                # to the Person's own avatar for people-only records.
                "avatar": p.linked_user.avatar or p.avatar,
                "colour": p.linked_user.colour or p.colour,
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


class UserPreferenceView(APIView):
    """The caller's own UI preferences (tab order, mobile dock shortcuts).

    Self-service by design: arranging your own interface needs no elevated permission, and the
    values carry no authority — see apps.accounts.preferences. It is still per-login state, so
    it needs a login: the project default is AllowAny, which would otherwise reach the queries
    below with an AnonymousUser.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response(services.get_user_preferences(request.user))

    def patch(self, request: Request) -> Response:
        from apps.accounts import preferences

        if not isinstance(request.data, dict) or not request.data:
            raise ValidationError({"detail": "Provide at least one preference to update."})
        unknown = [key for key in request.data if not preferences.is_supported(key)]
        if unknown:
            raise ValidationError({key: "Unknown preference." for key in unknown})
        for key, value in request.data.items():
            # Tab order merges per page so a client that only knows its own page cannot wipe
            # the orderings for every other page.
            if key == preferences.TAB_ORDER:
                if not isinstance(value, dict):
                    raise ValidationError({key: "Expected an object of page orders."})
                services.merge_tab_order(request.user, value)
            else:
                services.set_user_preference(request.user, key, value)
        return Response(services.get_user_preferences(request.user))

    def delete(self, request: Request) -> Response:
        from apps.accounts import preferences

        key = request.query_params.get("key")
        keys = [key] if key else list(preferences.REGISTRY)
        for entry in keys:
            services.reset_user_preference(request.user, entry)
        return Response(services.get_user_preferences(request.user))


class GuideDismissalView(APIView):
    """Self-service, versioned guide preferences for the current login."""

    # Same reason as UserPreferenceView: per-login state under an AllowAny default.
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        rows = request.user.guide_dismissals.all()
        return Response([
            {"guide_identifier": row.guide_identifier, "guide_version": row.guide_version}
            for row in rows
        ])

    def post(self, request: Request) -> Response:
        serializer = GuideDismissalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = services.dismiss_guide(request.user, **serializer.validated_data)
        return Response(
            {"guide_identifier": row.guide_identifier, "guide_version": row.guide_version},
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request: Request) -> Response:
        count = services.reset_guide_dismissals(request.user)
        return Response({"removed": count})
