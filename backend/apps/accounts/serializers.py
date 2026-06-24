"""
accounts serializers — input validation and output representation for auth endpoints.
"""
from rest_framework import serializers

from apps.accounts.models import User


class PinLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=50)
    pin = serializers.CharField(max_length=10, write_only=True)


class PasswordLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=50)
    password = serializers.CharField(write_only=True)


class ReauthSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)


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
