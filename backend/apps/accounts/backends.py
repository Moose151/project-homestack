"""
Authentication backends for HomeStack (D6).

PinBackend    — avatar + PIN login for all members including children.
PasswordBackend — full password login for admin/manager accounts only
                  (and as the gate for sensitive re-authentication, Phase 1.5+).

Both backends are listed in AUTHENTICATION_BACKENDS so Django's authenticate()
tries PIN first, then password.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.http import HttpRequest

    from apps.accounts.models import User


class PinBackend:
    """Authenticate any active, non-soft-deleted user by username + PIN."""

    def authenticate(
        self, request: "HttpRequest | None", username: str | None = None, pin: str | None = None
    ) -> "User | None":
        if username is None or pin is None:
            return None
        from apps.accounts.models import User as UserModel

        try:
            user = UserModel.objects.get(username=username)
        except UserModel.DoesNotExist:
            # Run a dummy check to maintain consistent timing (mitigate user enumeration).
            UserModel().check_pin(pin)
            return None
        if user.is_active and user.check_pin(pin):
            return user
        return None

    def get_user(self, user_id: int) -> "User | None":
        from apps.accounts.models import User as UserModel

        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None


class PasswordBackend:
    """Authenticate non-child active users by username + password.

    Child accounts never have a usable password (set_unusable_password on creation),
    so this backend naturally rejects them.
    """

    def authenticate(
        self, request: "HttpRequest | None", username: str | None = None, password: str | None = None
    ) -> "User | None":
        if username is None or password is None:
            return None
        from apps.accounts.models import User as UserModel

        try:
            user = UserModel.objects.get(username=username)
        except UserModel.DoesNotExist:
            UserModel().check_password(password)
            return None
        if user.is_active and not user.is_child_account and user.check_password(password):
            return user
        return None

    def get_user(self, user_id: int) -> "User | None":
        from apps.accounts.models import User as UserModel

        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
