"""
accounts services — auth business logic (D6).

All session manipulation lives here so views stay thin (Coding Standards §6).
"""
from __future__ import annotations

from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest

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


def grant_reauth(request: HttpRequest) -> None:
    """Mark the session as having passed password re-authentication (D6 §6)."""
    request.session[REAUTH_SESSION_KEY] = True


def revoke_reauth(request: HttpRequest) -> None:
    request.session.pop(REAUTH_SESSION_KEY, None)


def is_reauthed(request: HttpRequest) -> bool:
    return bool(request.session.get(REAUTH_SESSION_KEY, False))


def reauth_user(request: HttpRequest, password: str) -> bool:
    """Re-authenticate the currently logged-in user with their password (D6 §6).

    Returns True and sets the elevated session flag if successful.
    Child accounts and guests cannot re-auth (no password).
    """
    user = request.user
    if not user.is_authenticated or user.is_child_account:
        return False
    if not user.check_password(password):
        return False
    grant_reauth(request)
    return True
