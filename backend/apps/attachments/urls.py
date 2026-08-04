from django.urls import path

from apps.attachments import views


urlpatterns = [
    path("", views.AttachmentListCreateView.as_view(), name="attachment-list"),
    path("<int:attachment_id>/", views.AttachmentDetailView.as_view(), name="attachment-detail"),
    path(
        "<int:attachment_id>/download/",
        views.AttachmentDownloadView.as_view(),
        name="attachment-download",
    ),
]
