from django.urls import path

from apps.hub.views import (
    HouseholdWidgetView,
    HubView,
    HubWidgetConfigView,
    KioskHubView,
    UpcomingCompleteView,
    UpcomingDismissalView,
    UserWidgetOrderView,
    UserWidgetView,
)

urlpatterns = [
    path("", HubView.as_view(), name="hub"),
    path("kiosk/", KioskHubView.as_view(), name="kiosk-hub"),
    path("widgets/", HubWidgetConfigView.as_view(), name="hub-widget-config"),
    path("widgets/me/order/", UserWidgetOrderView.as_view(), name="hub-widget-user-order"),
    path(
        "upcoming/<int:event_id>/complete/",
        UpcomingCompleteView.as_view(),
        name="hub-upcoming-complete",
    ),
    path(
        "upcoming/<int:event_id>/dismiss/",
        UpcomingDismissalView.as_view(),
        name="hub-upcoming-dismissal",
    ),
    path("widgets/<str:key>/", HouseholdWidgetView.as_view(), name="hub-widget-household"),
    path("widgets/<str:key>/me/", UserWidgetView.as_view(), name="hub-widget-user"),
]
