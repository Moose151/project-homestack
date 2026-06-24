"""
audit views — read-only audit log list (admin only).

GET /api/v1/audit-logs/
"""
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer
from apps.permissions.drf import HomeStackPermission


class AuditLogListView(APIView):
    permission_classes = [HomeStackPermission.for_resource("audit")]
    # GET → "view" via default mapping

    def get(self, request: Request) -> Response:
        household = request.user.household
        logs = AuditLog.objects.filter(household=household).select_related(
            "user", "target_node"
        )[:200]
        return Response(AuditLogSerializer(logs, many=True).data)
