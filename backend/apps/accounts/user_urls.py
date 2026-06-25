"""User-management URLs — /api/v1/users/ (admin-only)."""
from django.urls import path

from apps.accounts.user_views import UserDetailView, UserListView

urlpatterns = [
    path("", UserListView.as_view(), name="user-list"),
    path("<int:user_id>/", UserDetailView.as_view(), name="user-detail"),
]
