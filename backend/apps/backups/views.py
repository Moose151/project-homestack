"""backups views — admin-only; create + restore require password re-auth (D17)."""
from __future__ import annotations

import io
import tarfile
from pathlib import Path

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.services import is_reauthed
from apps.backups import selectors, services
from apps.backups.serializers import BackupSerializer
from apps.permissions.drf import HomeStackPermission

_BackupPerm = HomeStackPermission.for_resource("backups")


class BackupListView(APIView):
    permission_classes = [_BackupPerm]

    def get(self, request: Request) -> Response:
        backups = selectors.list_backups()
        return Response(BackupSerializer(backups, many=True).data)

    def post(self, request: Request) -> Response:
        if not is_reauthed(request):
            raise PermissionDenied("Password re-authentication required.")
        backup = services.create_backup(request.user)
        return Response(BackupSerializer(backup).data, status=status.HTTP_201_CREATED)


class BackupDownloadView(APIView):
    permission_classes = [_BackupPerm]

    def get(self, request: Request, backup_id: int) -> StreamingHttpResponse:
        backup = selectors.get_backup(backup_id)
        if backup is None:
            raise NotFound()

        backup_path = services._backup_dir() / backup.label
        filename = f"{backup.label}.tar.gz"

        def _stream():
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w:gz") as tar:
                for name in ("db.dump", "media.tar.gz"):
                    p = backup_path / name
                    if p.exists():
                        tar.add(p, arcname=name)
            yield buf.getvalue()

        response = StreamingHttpResponse(
            streaming_content=_stream(),
            content_type="application/x-tar",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class BackupRestoreView(APIView):
    permission_classes = [_BackupPerm]
    permission_action = "restore"

    def post(self, request: Request, backup_id: int) -> Response:
        if not is_reauthed(request):
            raise PermissionDenied("Password re-authentication required.")
        backup = selectors.get_backup(backup_id)
        if backup is None:
            raise NotFound()
        try:
            services.restore_backup(backup, request.user)
        except ValueError as exc:
            raise ValidationError(str(exc))
        return Response({"detail": "Restore complete."})
