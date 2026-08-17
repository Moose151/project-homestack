"""
accounts serializers — input validation and output representation for auth endpoints.
"""
from rest_framework import serializers

from apps.accounts.models import User


class PinLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=50)
    pin = serializers.CharField(max_length=10, write_only=True)
    # Which screen this is. Only "web" earns the longer elevation window; see
    # apps.accounts.services.reauth_ttl_seconds.
    surface = serializers.CharField(max_length=20, required=False, allow_blank=True)


class PasswordLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=50)
    password = serializers.CharField(write_only=True)
    surface = serializers.CharField(max_length=20, required=False, allow_blank=True)


class ReauthSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)


class GuideDismissalSerializer(serializers.Serializer):
    guide_identifier = serializers.RegexField(r"^[a-z0-9][a-z0-9_.-]*$", max_length=100)
    guide_version = serializers.CharField(max_length=50, default="1")


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "display_name",
            "username",
            "email",
            "avatar",
            "role",
            "is_active",
            "is_child_account",
            "colour",
            "last_login",
            "created_at",
        ]
        read_only_fields = fields


class UserAdminSerializer(serializers.ModelSerializer):
    """Read representation for the admin user-management screen (includes linked person)."""

    linked_person_id = serializers.SerializerMethodField()
    linked_person_name = serializers.SerializerMethodField()
    has_password = serializers.SerializerMethodField()
    solace_access = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "display_name", "username", "email", "avatar", "role",
            "is_active", "is_child_account", "colour", "last_login", "created_at",
            "linked_person_id", "linked_person_name", "has_password",
            "solace_access",
        ]
        read_only_fields = fields

    def _person(self, obj):
        return getattr(obj, "person_profile", None)

    def get_linked_person_id(self, obj):
        p = self._person(obj)
        return p.id if p else None

    def get_linked_person_name(self, obj):
        p = self._person(obj)
        return p.display_name if p else None

    def get_has_password(self, obj) -> bool:
        return obj.has_usable_password()

    def get_solace_access(self, obj) -> bool:
        from apps.permissions.resolver import resolve_permission

        return resolve_permission(obj, "view", "solace")


class UserWriteSerializer(serializers.Serializer):
    """Create/update payload for user management. PIN/password optional on update."""

    username = serializers.CharField(max_length=50, required=False)
    display_name = serializers.CharField(max_length=100, required=False)
    role = serializers.ChoiceField(choices=User.Role.choices, required=False)
    email = serializers.EmailField(required=False, allow_blank=True)
    colour = serializers.CharField(max_length=7, required=False, allow_blank=True)
    avatar = serializers.CharField(max_length=255, required=False, allow_blank=True)
    is_child_account = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)
    pin = serializers.CharField(max_length=10, required=False, allow_blank=True, write_only=True)
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    # Person linking (create only): attach an existing unlinked person, or make a new one.
    link_person_id = serializers.IntegerField(required=False, allow_null=True)
    create_person = serializers.BooleanField(required=False)
    # Solace is denied to non-admin roles by default. Admin onboarding may deliberately grant
    # the complete node permission set to a trusted adult without promoting them to admin.
    solace_access = serializers.BooleanField(required=False)

    def validate_pin(self, value: str) -> str:
        if value and not (value.isdigit() and 4 <= len(value) <= 6):
            raise serializers.ValidationError("PIN must be 4–6 digits.")
        return value

    def validate_username(self, value: str) -> str:
        if value is not None and not value.strip():
            raise serializers.ValidationError("Username may not be blank.")
        return value
