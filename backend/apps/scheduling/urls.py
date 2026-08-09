from django.urls import path

from apps.scheduling.views import (
    CalendarEventDetailView,
    CalendarEventListView,
    RotatingScheduleDetailView,
    RotatingScheduleExceptionDetailView,
    RotatingScheduleListView,
    RotatingScheduleOccurrenceListView,
)

urlpatterns = [
    path("events/", CalendarEventListView.as_view(), name="calendar-event-list"),
    path("events/<int:event_id>/", CalendarEventDetailView.as_view(), name="calendar-event-detail"),
    path("rotations/", RotatingScheduleListView.as_view(), name="rotating-schedule-list"),
    path(
        "rotations/<int:schedule_id>/",
        RotatingScheduleDetailView.as_view(),
        name="rotating-schedule-detail",
    ),
    path(
        "rotation-occurrences/",
        RotatingScheduleOccurrenceListView.as_view(),
        name="rotating-schedule-occurrence-list",
    ),
    path(
        "rotations/<int:schedule_id>/exceptions/<str:date>/",
        RotatingScheduleExceptionDetailView.as_view(),
        name="rotating-schedule-exception-detail",
    ),
]
