"""Permission-filtered attachment reads."""
from __future__ import annotations

from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from apps.attachments.models import Attachment
from apps.permissions.resolver import resolve_permission
from apps.permissions.visibility import apply_visibility


def list_attachments(
    user,
    *,
    sensitive_unlocked: bool,
    linked_node=None,
    linked_record_type: str | None = None,
    linked_record_id: int | None = None,
) -> QuerySet[Attachment]:
    qs = apply_visibility(
        Attachment.objects.filter(household=user.household).select_related(
            "uploaded_by", "linked_node"
        ),
        user,
    )
    if getattr(user, "is_child_account", False) or not sensitive_unlocked:
        qs = qs.exclude(
            Q(visibility=Attachment.Visibility.SENSITIVE)
            | ~Q(sensitivity=Attachment.Sensitivity.NORMAL)
        )
    if linked_node is not None:
        qs = qs.filter(linked_node=linked_node)
    if linked_record_type is not None and linked_record_id is not None:
        qs = qs.filter(
            linked_record_type=linked_record_type,
            linked_record_id=linked_record_id,
        )
    return qs


def get_attachment_for_user(
    user,
    attachment_id: int,
    *,
    action: str,
    sensitive_unlocked: bool,
) -> Attachment:
    visible = apply_visibility(
        Attachment.objects.filter(household=user.household).select_related("linked_node"),
        user,
    )
    attachment = get_object_or_404(visible, pk=attachment_id)
    if not resolve_permission(
        user,
        action,
        "attachments",
        record=attachment,
        sensitive_unlocked=sensitive_unlocked,
    ):
        raise PermissionDenied("Password re-authentication or additional access is required.")
    return attachment
