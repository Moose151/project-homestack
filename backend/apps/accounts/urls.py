"""accounts URL config — all auth endpoints live under /api/v1/auth/."""
from django.urls import path

from apps.accounts import views

urlpatterns = [
    path("pin-login/", views.PinLoginView.as_view(), name="auth-pin-login"),
    path("password-login/", views.PasswordLoginView.as_view(), name="auth-password-login"),
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("me/", views.MeView.as_view(), name="auth-me"),
    path("reauth/", views.ReauthView.as_view(), name="auth-reauth"),
    path("kiosk-users/", views.KioskUsersView.as_view(), name="kiosk-users"),
]
