"""Attachment writes and download auditing."""
from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
from uuid import uuid4

from apps.attachments.models import Attachment
from apps.audit.helpers import log_audit
from apps.core.models import get_active_household


def _checksum(uploaded_file) -> str:
    digest = hashlib.sha256()
    for chunk in uploaded_file.chunks():
        digest.update(chunk)
    uploaded_file.seek(0)
    return digest.hexdigest()


def create_attachment(*, uploaded_file, acting_user, request=None, **fields) -> Attachment:
    original_filename = Path(uploaded_file.name).name[:255] or "attachment"
    suffix = Path(original_filename).suffix.lower()[:20]
    stored_filename = f"{uuid4().hex}{suffix}"
    mime_type = (
        getattr(uploaded_file, "content_type", "")
        or mimetypes.guess_type(original_filename)[0]
        or "application/octet-stream"
    )[:255]
    attachment = Attachment.objects.create(
        household=get_active_household(),
        uploaded_by=acting_user,
        filename=stored_filename,
        original_filename=original_filename,
        file_path=uploaded_file,
        mime_type=mime_type,
        file_size=uploaded_file.size,
        checksum=_checksum(uploaded_file),
        created_by=acting_user,
        updated_by=acting_user,
        **fields,
    )
    log_audit(
        "attachment_uploaded",
        user=acting_user,
        target_node=attachment.linked_node,
        target_record_type="attachments.Attachment",
        target_record_id=attachment.id,
        request=request,
        metadata={"sensitivity": attachment.sensitivity},
    )
    return attachment


def delete_attachment(attachment: Attachment, *, acting_user, request=None) -> None:
    attachment.updated_by = acting_user
    attachment.save(update_fields=["updated_by", "updated_at"])
    attachment.soft_delete()
    log_audit(
        "attachment_deleted",
        user=acting_user,
        target_node=attachment.linked_node,
        target_record_type="attachments.Attachment",
        target_record_id=attachment.id,
        request=request,
        metadata={"sensitivity": attachment.sensitivity},
    )


def audit_download(attachment: Attachment, *, acting_user, request=None) -> None:
    if not attachment.is_sensitive:
        return
    log_audit(
        "sensitive_attachment_downloaded",
        user=acting_user,
        target_node=attachment.linked_node,
        target_record_type="attachments.Attachment",
        target_record_id=attachment.id,
        request=request,
        metadata={"sensitivity": attachment.sensitivity},
    )
