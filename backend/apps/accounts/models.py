"""
accounts.User — the custom user model for HomeStack (D6, D12).

Combines AbstractBaseUser (password hashing, session auth, is_authenticated) with
HouseholdBaseModel (household FK, soft delete, created/updated_by audit).

Auth flow (D6):
  - All members log in with avatar + PIN (low-entropy, Argon2id-hashed in `pin_hash`).
  - Admins and managers also have a password (stored in AbstractBaseUser.`password`),
    used for sensitive re-authentication (D6 §6) and for admin-panel access.
  - Children never receive a password; their `password` is set unusable on creation.
  - PIN is never the sole gate for sensitive data.
"""
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.hashers import check_password, make_password
from django.db import models

from apps.core.models import AllObjectsManager, HouseholdBaseModel, HouseholdManager


class UserManager(HouseholdManager):
    """Manager for accounts.User.

    Extends HouseholdManager (excludes soft-deleted, scoped to household) and adds the
    create_user / create_superuser helpers required by AbstractBaseUser / Django admin.
    """

    use_in_migrations = True

    def _make_user(self, username, display_name, role, password, **extra_fields):
        from apps.core.models import get_active_household

        if not username:
            raise ValueError("username is required")
        if not display_name:
            raise ValueError("display_name is required")
        household = get_active_household()
        user = self.model(
            username=username,
            display_name=display_name,
            role=role,
            household=household,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, display_name, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.USER)
        return self._make_user(username, display_name, extra_fields.pop("role"), password, **extra_fields)

    def create_superuser(self, username, display_name, password=None, **extra_fields):
        return self._make_user(username, display_name, User.Role.ADMIN, password, **extra_fields)


class User(AbstractBaseUser, HouseholdBaseModel):
    """HomeStack user account (D6, D12).

    Fields
    ------
    display_name    Shown in the UI (e.g. "Mum", "Finn").
    username        Unique login handle.
    email           Optional; adults may have one for future notifications.
    avatar          Colour name or image path used on the avatar-selection screen.
    pin_hash        Argon2id hash of the 4–6-digit PIN (all users).
    password        AbstractBaseUser field — Argon2id hash of the full password
                    (admin/manager only; set unusable for child/guest accounts).
    role            admin | manager | user | guest.
    is_active       False = account disabled; excluded from auth.
    is_child_account Enforces kiosk-safe content and disables password login.
    colour          Hex colour for avatar ring / UI accents (e.g. "#4A90E2").
    last_login      AbstractBaseUser field — updated by Django's login() signal.

    Inherited from HouseholdBaseModel
    ----------------------------------
    household, created_at, updated_at, created_by, updated_by, deleted_at
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MANAGER = "manager", "Manager"
        USER = "user", "User"
        GUEST = "guest", "Guest"

    display_name = models.CharField(max_length=100)
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(blank=True, default="")
    avatar = models.CharField(max_length=255, blank=True, default="")
    pin_hash = models.CharField(max_length=255, blank=True, default="")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    is_active = models.BooleanField(default=True)
    is_child_account = models.BooleanField(default=False)
    colour = models.CharField(max_length=7, blank=True, default="")

    # AbstractBaseUser provides: password (password_hash), last_login
    # HouseholdBaseModel provides: household, created_at, updated_at,
    #                              created_by, updated_by, deleted_at

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["display_name"]

    objects = UserManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self) -> str:
        return self.display_name

    # --- PIN helpers ---

    def set_pin(self, raw_pin: str) -> None:
        """Hash raw_pin with Argon2id and store in pin_hash."""
        self.pin_hash = make_password(raw_pin)

    def check_pin(self, raw_pin: str) -> bool:
        """Return True if raw_pin matches the stored Argon2id hash."""
        if not self.pin_hash:
            return False
        return check_password(raw_pin, self.pin_hash)

    # --- Django admin compatibility (no PermissionsMixin — custom resolver in Phase 1.5) ---

    @property
    def is_staff(self) -> bool:
        return self.role in (self.Role.ADMIN, self.Role.MANAGER)

    def has_perm(self, perm, obj=None) -> bool:  # noqa: ANN001
        return self.is_active and self.role == self.Role.ADMIN

    def has_module_perms(self, app_label) -> bool:  # noqa: ANN001
        return self.is_active and self.role == self.Role.ADMIN
