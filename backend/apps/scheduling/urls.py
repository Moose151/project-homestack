from django.urls import path

from apps.scheduling.views import (
    CalendarEventDetailView,
    CalendarEventListView,
    CalendarSourceDetailView,
    CalendarSourceListView,
    CalendarSourcePreviewView,
    CalendarSourceSyncView,
    RotatingScheduleDetailView,
    RotatingScheduleExceptionDetailView,
    RotatingScheduleListView,
    RotatingScheduleOccurrenceListView,
)

urlpatterns = [
    path("events/", CalendarEventListView.as_view(), name="calendar-event-list"),
    path("events/<int:event_id>/", CalendarEventDetailView.as_view(), name="calendar-event-detail"),
    path("sources/", CalendarSourceListView.as_view(), name="calendar-source-list"),
    path("sources/preview/", CalendarSourcePreviewView.as_view(), name="calendar-source-preview"),
    path("sources/<int:source_id>/", CalendarSourceDetailView.as_view(), name="calendar-source-detail"),
    path("sources/<int:source_id>/sync/", CalendarSourceSyncView.as_view(), name="calendar-source-sync"),
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
