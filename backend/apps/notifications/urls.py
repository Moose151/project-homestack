from django.urls import path

from apps.notifications.views import (
    NotificationListView,
    NotificationPreferenceListView,
    NotificationReadAllView,
    NotificationReadView,
    NotificationSettingsView,
)

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("read-all/", NotificationReadAllView.as_view(), name="notification-read-all"),
    path("<int:notification_id>/read/", NotificationReadView.as_view(), name="notification-read"),
    path("preferences/", NotificationPreferenceListView.as_view(), name="notification-preferences"),
    path("settings/", NotificationSettingsView.as_view(), name="notification-settings"),
]
