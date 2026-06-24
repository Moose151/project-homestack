"""backups selectors."""
from __future__ import annotations

from apps.backups.models import Backup


def list_backups():
    return Backup.objects.all()


def get_backup(pk: int) -> Backup | None:
    try:
        return Backup.objects.get(pk=pk)
    except Backup.DoesNotExist:
        return None
