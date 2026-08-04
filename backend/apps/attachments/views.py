"""Thin attachment API views; policy lives in the resolver/selectors/services."""
from __future__ import annotations

from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.services import is_reauthed
from apps.attachments import selectors, services
from apps.attachments.serializers import (
    AttachmentFilterSerializer,
    AttachmentSerializer,
    AttachmentUploadSerializer,
)
from apps.permissions.drf import HomeStackPermission


_AttachmentPerm = HomeStackPermission.for_resource("attachments")


class AttachmentListCreateView(APIView):
    permission_classes = [_AttachmentPerm]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request: Request) -> Response:
        filters = AttachmentFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        attachments = selectors.list_attachments(
            request.user,
            sensitive_unlocked=is_reauthed(request._request),
            **filters.validated_data,
        )
        return Response(AttachmentSerializer(attachments, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = AttachmentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        uploaded_file = data.pop("file")
        attachment = services.create_attachment(
            uploaded_file=uploaded_file,
            acting_user=request.user,
            request=request._request,
            **data,
        )
        return Response(AttachmentSerializer(attachment).data, status=status.HTTP_201_CREATED)


class AttachmentDownloadView(APIView):
    permission_classes = [_AttachmentPerm]

    def get(self, request: Request, attachment_id: int):
        attachment = selectors.get_attachment_for_user(
            request.user,
            attachment_id,
            action="view",
            sensitive_unlocked=is_reauthed(request._request),
        )
        if not attachment.file_path or not attachment.file_path.storage.exists(attachment.file_path.name):
            raise Http404("Attachment file is missing.")
        services.audit_download(
            attachment,
            acting_user=request.user,
            request=request._request,
        )
        return FileResponse(
            attachment.file_path.open("rb"),
            as_attachment=True,
            filename=attachment.original_filename,
            content_type=attachment.mime_type,
        )


class AttachmentDetailView(APIView):
    permission_classes = [_AttachmentPerm]

    def delete(self, request: Request, attachment_id: int) -> Response:
        attachment = selectors.get_attachment_for_user(
            request.user,
            attachment_id,
            action="delete",
            sensitive_unlocked=is_reauthed(request._request),
        )
        services.delete_attachment(
            attachment,
            acting_user=request.user,
            request=request._request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
