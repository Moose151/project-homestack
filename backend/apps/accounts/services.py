"""
accounts services — auth business logic (D6).

All session manipulation lives here so views stay thin (Coding Standards §6).
"""
from __future__ import annotations

from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone

from apps.accounts.models import User

# Session key used to flag a short-lived elevated (re-auth) state (D6 §6).
REAUTH_SESSION_KEY = "_homestack_reauth"


def pin_login_user(request: HttpRequest, username: str, pin: str) -> User | None:
    """Authenticate via PIN and start a session. Returns the user or None."""
    from apps.audit.helpers import log_audit
    from apps.accounts.selectors import get_user_by_username

    user = authenticate(request, username=username, pin=pin)
    if user is None:
        failed_user = get_user_by_username(username)
        log_audit("login_failed", user=failed_user, request=request,
                  metadata={"method": "pin", "username": username})
        return None
    login(request, user, backend="apps.accounts.backends.PinBackend")
    log_audit("login", user=user, request=request, metadata={"method": "pin"})
    return user


def password_login_user(request: HttpRequest, username: str, password: str) -> User | None:
    """Authenticate via password and start a session. Returns the user or None."""
    from apps.audit.helpers import log_audit
    from apps.accounts.selectors import get_user_by_username

    user = authenticate(request, username=username, password=password)
    if user is None:
        failed_user = get_user_by_username(username)
        log_audit("login_failed", user=failed_user, request=request,
                  metadata={"method": "password", "username": username})
        return None
    login(request, user, backend="apps.accounts.backends.PasswordBackend")
    log_audit("login", user=user, request=request, metadata={"method": "password"})
    return user


def logout_user(request: HttpRequest) -> None:
    logout(request)


KIOSK_SESSION_KEY = "hs_surface_is_kiosk"


def mark_session_surface(request: HttpRequest, surface: str) -> None:
    """Remember whether this session is a kiosk one, so elevation can expire sooner.

    Anything other than an explicit "web" counts as the kiosk: a client that does not say which
    surface it is gets the cautious window rather than the generous one.
    """
    request.session[KIOSK_SESSION_KEY] = (surface or "").strip().lower() != "web"


def session_is_kiosk(request: HttpRequest) -> bool:
    return bool(request.session.get(KIOSK_SESSION_KEY, False))


def reauth_ttl_seconds(request: HttpRequest) -> int:
    if session_is_kiosk(request):
        return getattr(settings, "KIOSK_REAUTH_TTL_SECONDS", 60)
    return getattr(settings, "REAUTH_TTL_SECONDS", 5 * 60)


def grant_reauth(request: HttpRequest) -> None:
    """Mark the session as having passed password re-authentication (D6 §6)."""
    request.session[REAUTH_SESSION_KEY] = int(timezone.now().timestamp())


def revoke_reauth(request: HttpRequest) -> None:
    request.session.pop(REAUTH_SESSION_KEY, None)


def is_reauthed(request: HttpRequest) -> bool:
    granted_at = request.session.get(REAUTH_SESSION_KEY)
    # Old releases stored a permanent boolean. Refuse it so upgrades cannot retain an
    # indefinitely elevated session.
    if isinstance(granted_at, bool) or not isinstance(granted_at, (int, float)):
        if granted_at is not None:
            revoke_reauth(request)
        return False
    ttl_seconds = reauth_ttl_seconds(request)
    age = timezone.now().timestamp() - granted_at
    if age < 0 or age > ttl_seconds:
        revoke_reauth(request)
        return False
    return True


def reauth_user(request: HttpRequest, password: str) -> bool:
    """Re-authenticate the currently logged-in user with their password (D6 §6).

    Returns True and sets the elevated session flag if successful.
    Child accounts and guests cannot re-auth (no password).
    """
    user = request.user
    if (
        not user.is_authenticated
        or user.is_child_account
        or user.role == User.Role.GUEST
    ):
        return False
    if not user.check_password(password):
        return False
    grant_reauth(request)
    return True


def dismiss_guide(user: User, *, guide_identifier: str, guide_version: str = "1"):
    from apps.accounts.models import GuideDismissal

    dismissal, _ = GuideDismissal.objects.update_or_create(
        user=user,
        guide_identifier=guide_identifier,
        guide_version=guide_version,
        defaults={
            "household": user.household,
            "created_by": user,
            "updated_by": user,
            "deleted_at": None,
        },
    )
    return dismissal


def reset_guide_dismissals(user: User) -> int:
    from apps.accounts.models import GuideDismissal

    count, _ = GuideDismissal.objects.filter(user=user).delete()
    return count


def get_user_preferences(user: User) -> dict:
    """Every supported preference for this user, with defaults filled in for unset keys."""
    from apps.accounts import preferences
    from apps.accounts.models import UserPreference

    stored = {
        row.key: row.value
        for row in UserPreference.objects.filter(user=user)
        if preferences.is_supported(row.key)
    }
    return {
        key: stored.get(key, preferences.default_for(key))
        for key in preferences.REGISTRY
    }


def set_user_preference(user: User, key: str, value):
    """Validate and store one preference, returning the normalised value.

    Storing an empty value removes the row instead, so "reset" and "save nothing" converge on
    one state rather than leaving an empty record that reads as a deliberate choice.
    """
    from apps.accounts import preferences
    from apps.accounts.models import UserPreference

    normalised = preferences.validate(key, value)
    if not normalised:
        UserPreference.objects.filter(user=user, key=key).delete()
        return preferences.default_for(key)
    UserPreference.objects.update_or_create(
        user=user,
        key=key,
        defaults={
            "value": normalised,
            "household": user.household,
            "created_by": user,
            "updated_by": user,
            "deleted_at": None,
        },
    )
    return normalised


def merge_tab_order(user: User, pages: dict) -> dict:
    """Merge per-page tab orders into the stored map.

    Merging rather than replacing means a client that only knows about the page it is on
    cannot wipe the user's ordering for every other page. A page mapped to null or an empty
    list is removed, which is how a single page resets to default.
    """
    from apps.accounts import preferences

    incoming = preferences.validate(preferences.TAB_ORDER, pages)
    current = dict(get_user_preferences(user)[preferences.TAB_ORDER])
    for page, tabs in pages.items():
        if not tabs:
            current.pop(page, None)
    current.update(incoming)
    return set_user_preference(user, preferences.TAB_ORDER, current)


def reset_user_preference(user: User, key: str):
    from apps.accounts import preferences
    from apps.accounts.models import UserPreference

    if not preferences.is_supported(key):
        from rest_framework import serializers as drf_serializers
        raise drf_serializers.ValidationError({key: "Unknown preference."})
    UserPreference.objects.filter(user=user, key=key).delete()
    return preferences.default_for(key)
