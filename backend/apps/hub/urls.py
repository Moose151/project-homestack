from django.urls import path

from apps.hub.views import (
    HouseholdWidgetView,
    HubView,
    HubWidgetConfigView,
    KioskHubView,
    UserWidgetView,
)

urlpatterns = [
    path("", HubView.as_view(), name="hub"),
    path("kiosk/", KioskHubView.as_view(), name="kiosk-hub"),
    path("widgets/", HubWidgetConfigView.as_view(), name="hub-widget-config"),
    path("widgets/<str:key>/", HouseholdWidgetView.as_view(), name="hub-widget-household"),
    path("widgets/<str:key>/me/", UserWidgetView.as_view(), name="hub-widget-user"),
]
