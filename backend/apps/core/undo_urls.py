from django.urls import path

from apps.core.undo_views import RestoreRecordView

urlpatterns = [
    path("restore/", RestoreRecordView.as_view(), name="undo-restore"),
]
