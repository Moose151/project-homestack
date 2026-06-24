"""accounts admin — basic registration so users are visible in the Django admin panel."""
from django.contrib import admin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms

from apps.accounts.models import User


class UserAdminCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "display_name", "role")


class UserAdminChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    list_display = ("username", "display_name", "role", "is_active", "is_child_account")
    list_filter = ("role", "is_active", "is_child_account")
    search_fields = ("username", "display_name", "email")
    ordering = ("display_name",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Profile", {"fields": ("display_name", "email", "avatar", "colour", "role", "is_child_account")}),
        ("Status", {"fields": ("is_active",)}),
        ("Household", {"fields": ("household",)}),
        ("Important dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "display_name", "role", "password1", "password2"),
            },
        ),
    )
    readonly_fields = ("last_login", "created_at", "updated_at")

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            kwargs["form"] = self.add_form
        return super().get_form(request, obj, **kwargs)
