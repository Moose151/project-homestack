from django.urls import path

from apps.scheduling.views import CalendarEventDetailView, CalendarEventListView

urlpatterns = [
    path("events/", CalendarEventListView.as_view(), name="calendar-event-list"),
    path("events/<int:event_id>/", CalendarEventDetailView.as_view(), name="calendar-event-detail"),
]
