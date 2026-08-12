from django.urls import path

from apps.notifications.views import (
    NotificationListView,
    NotificationPreferenceListView,
    NotificationReadAllView,
    NotificationReadView,
    NotificationSettingsView,
    PushDeviceDetailView,
    PushDeviceListView,
    PushDeviceTestView,
    VapidPublicKeyView,
)

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("read-all/", NotificationReadAllView.as_view(), name="notification-read-all"),
    path("<int:notification_id>/read/", NotificationReadView.as_view(), name="notification-read"),
    path("preferences/", NotificationPreferenceListView.as_view(), name="notification-preferences"),
    path("settings/", NotificationSettingsView.as_view(), name="notification-settings"),
    path("vapid-public-key/", VapidPublicKeyView.as_view(), name="notification-vapid-public-key"),
    path("devices/", PushDeviceListView.as_view(), name="notification-devices"),
    path("devices/<int:device_id>/", PushDeviceDetailView.as_view(), name="notification-device-detail"),
    path("devices/<int:device_id>/test/", PushDeviceTestView.as_view(), name="notification-device-test"),
]
