"""Restore a record the caller just deleted (see apps/core/undo.py for the why)."""
from __future__ import annotations

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.services import is_reauthed
from apps.audit.helpers import log_audit
from apps.core.undo import restorable_for
from apps.nodes.access import node_requires_reauth
from apps.permissions.resolver import resolve_permission


class RestoreRecordView(APIView):
    """POST {record_type, record_id} to undo a soft delete.

    Permission is the owning node's own `delete` right, resolved centrally: being allowed to
    delete a thing is exactly the right to put it back. Restoring is strictly less destructive
    than the delete it reverses, so it never needs a wider grant than the delete did.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        record_type = str(request.data.get("record_type") or "")
        record_id = request.data.get("record_id")
        entry = restorable_for(record_type)
        if entry is None or record_id in (None, ""):
            return Response(
                {"detail": "That item cannot be restored."},
                status=status.HTTP_404_NOT_FOUND,
            )
        reauthed = is_reauthed(request._request)
        if not resolve_permission(
            request.user, "delete", entry.resource, sensitive_unlocked=reauthed,
        ):
            return Response(
                {"detail": "You cannot restore this item."},
                status=status.HTTP_403_FORBIDDEN,
            )
        # A sensitive node's own views sit behind a lock and audit every request that passes it
        # (apps/nodes/access.py). This endpoint reaches into those nodes too, so it applies the
        # same gate rather than becoming the one way in that neither locks nor records.
        if entry.sensitive_node:
            if node_requires_reauth(entry.sensitive_node) and not reauthed:
                return Response(
                    {"detail": "Unlock this area before restoring."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            self._audit_sensitive_access(request, entry, record_type)
        try:
            record = entry.load(int(record_id))
        except (TypeError, ValueError):
            record = None
        if record is None:
            # Already restored, never deleted, or not a real id — all the same to the caller,
            # and saying which would leak whether the record exists.
            return Response(
                {"detail": "That item is no longer available to restore."},
                status=status.HTTP_404_NOT_FOUND,
            )
        # A restore is several writes — the row, its Calendar projection, a bucket balance —
        # and a partial one is worse than the delete it reverses.
        with transaction.atomic():
            entry.restore(request.user, record)
        return Response({"restored": True, "noun": entry.noun})

    @staticmethod
    def _audit_sensitive_access(request: Request, entry, record_type: str) -> None:
        from apps.nodes.models import Node

        log_audit(
            "sensitive_node_accessed",
            user=request.user,
            target_node=Node.objects.filter(key=entry.sensitive_node).first(),
            request=request._request,
            metadata={
                "node": entry.sensitive_node,
                "surface": "undo_restore",
                "record_type": record_type,
                "path": request.path,
                "method": request.method,
            },
        )
