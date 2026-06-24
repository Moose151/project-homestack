from django.urls import path

from apps.hub.views import HubView, KioskHubView

urlpatterns = [
    path("", HubView.as_view(), name="hub"),
    path("kiosk/", KioskHubView.as_view(), name="kiosk-hub"),
]
