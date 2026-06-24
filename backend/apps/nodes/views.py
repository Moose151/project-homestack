"""
nodes views — thin wrappers delegating to services/selectors (D10).

Endpoints:
  GET   /api/v1/nodes/                      — list all nodes with household state
  POST  /api/v1/nodes/{key}/enable/         — admin: enable node
  POST  /api/v1/nodes/{key}/disable/        — admin: disable node
  PATCH /api/v1/nodes/{key}/settings/       — admin: update node settings
"""
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.nodes import selectors, services
from apps.nodes.models import Node
from apps.nodes.serializers import NodeSerializer, NodeSettingSerializer
from apps.permissions.drf import HomeStackPermission

_NodeViewPerm = HomeStackPermission.for_resource("nodes")


class NodeListView(APIView):
    permission_classes = [_NodeViewPerm]
    # GET → "view" via default mapping

    def get(self, request: Request) -> Response:
        nodes = selectors.list_household_nodes()
        return Response(NodeSerializer(nodes, many=True).data)


class NodeEnableView(APIView):
    permission_classes = [_NodeViewPerm]
    permission_action = "edit"  # POST would default to "create"; override to "edit"

    def post(self, request: Request, node_key: str) -> Response:
        try:
            hn = services.enable_node(request.user, node_key)
        except Node.DoesNotExist:
            return Response({"detail": "Node not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(NodeSerializer(hn).data)


class NodeDisableView(APIView):
    permission_classes = [_NodeViewPerm]
    permission_action = "edit"

    def post(self, request: Request, node_key: str) -> Response:
        try:
            hn = services.disable_node(request.user, node_key)
        except Node.DoesNotExist:
            return Response({"detail": "Node not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(NodeSerializer(hn).data)


class NodeSettingsView(APIView):
    permission_classes = [_NodeViewPerm]
    permission_action = "edit"  # PATCH would default to "edit" anyway, but explicit

    def patch(self, request: Request, node_key: str) -> Response:
        if not isinstance(request.data, dict):
            return Response(
                {"detail": "Body must be a JSON object of setting key-value pairs."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            settings = services.update_node_settings(request.user, node_key, request.data)
        except Node.DoesNotExist:
            return Response({"detail": "Node not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(NodeSettingSerializer(settings, many=True).data)
