from django.urls import path

from apps.link_imports.views import LinkPreviewView, LinkWatchDetailView, LinkWatchListView

urlpatterns = [
    path("preview/", LinkPreviewView.as_view(), name="link-import-preview"),
    path("watches/", LinkWatchListView.as_view(), name="link-watch-list"),
    path("watches/<int:watch_id>/", LinkWatchDetailView.as_view(), name="link-watch-detail"),
]
