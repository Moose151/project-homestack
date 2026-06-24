from django.urls import path

from apps.backups.views import BackupDownloadView, BackupListView, BackupRestoreView

urlpatterns = [
    path("", BackupListView.as_view(), name="backup-list"),
    path("<int:backup_id>/download/", BackupDownloadView.as_view(), name="backup-download"),
    path("<int:backup_id>/restore/", BackupRestoreView.as_view(), name="backup-restore"),
]
