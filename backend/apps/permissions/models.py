"""
permissions models — the central permission spine (D10).

Four tables:
  Permission       global catalogue of named permission codes (e.g. 'people.view')
  Role             per-household named role (admin/manager/user/guest are system roles)
  RolePermission   default permission grants per role
  UserPermission   per-user overrides; is_granted=False is an explicit deny

The resolver (resolver.py) combines these with re-auth state and returns allow/deny.
No ad-hoc permission checks belong in views; everything flows through the resolver (D10).
"""
from django.conf import settings
from django.db import models

from apps.core.models import HouseholdBaseModel


class Permission(models.Model):
    """Global catalogue of named permissions.

    Not a HouseholdBaseModel — permissions are system-wide definitions.
    code follows the pattern '{resource}.{action}' (e.g. 'people.view', 'atlas.create').
    """

    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    scope = models.CharField(max_length=50)  # resource group: 'people', 'atlas', 'global' …
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class Role(HouseholdBaseModel):
    """A named role within the household.

    System roles (admin, manager, user, guest) are seeded by migration and match
    User.Role choices. Custom roles may be added by admins in later milestones.
    """

    name = models.CharField(max_length=50)
    description = models.TextField(blank=True, default="")
    is_system_role = models.BooleanField(default=False)

    class Meta:
        unique_together = [("household", "name")]
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class RolePermission(models.Model):
    """Default permission grant for a role. Absence of a row means no default grant."""

    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(
        Permission, on_delete=models.CASCADE, related_name="role_permissions"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("role", "permission")]

    def __str__(self) -> str:
        return f"{self.role.name} → {self.permission.code}"


class UserPermission(HouseholdBaseModel):
    """Per-user permission override.

    is_granted=True  → explicit grant (adds to what the role gives)
    is_granted=False → explicit deny (blocks even if role would allow)

    These take precedence over role defaults in the resolver.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="permission_overrides",
    )
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    is_granted = models.BooleanField(default=True)

    class Meta:
        unique_together = [("user", "permission")]

    def __str__(self) -> str:
        verb = "grant" if self.is_granted else "deny"
        return f"{self.user} → {verb} {self.permission.code}"
