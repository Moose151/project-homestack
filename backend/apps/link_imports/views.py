from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.link_imports.extractors import extract_product
from apps.link_imports.fetch import LinkFetchError
from apps.link_imports.models import LinkWatch
from apps.link_imports.serializers import LinkPreviewSerializer, LinkWatchSerializer
from apps.link_imports.services import update_watch
from apps.link_imports.throttles import LinkPreviewThrottle
from apps.people.selectors import person_for_user
from apps.permissions.drf import HomeStackPermission


class LinkPreviewView(APIView):
    permission_classes = [HomeStackPermission.for_resource("link_imports")]
    throttle_classes = [LinkPreviewThrottle]

    def post(self, request: Request) -> Response:
        serializer = LinkPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            return Response(extract_product(serializer.validated_data["url"]))
        except LinkFetchError as exc:
            return Response({"detail": str(exc), "code": "link_preview_failed"}, status=422)


class LinkWatchListView(APIView):
    permission_classes = [HomeStackPermission.for_resource("link_imports")]

    def get(self, request: Request) -> Response:
        person = person_for_user(request.user)
        rows = LinkWatch.objects.filter(owner_person=person) if person else LinkWatch.objects.none()
        return Response(LinkWatchSerializer(rows, many=True).data)


class LinkWatchDetailView(APIView):
    permission_classes = [HomeStackPermission.for_resource("link_imports")]

    def patch(self, request: Request, watch_id: int) -> Response:
        person = person_for_user(request.user)
        row = LinkWatch.objects.filter(pk=watch_id, owner_person=person).first()
        if row is None:
            from rest_framework.exceptions import NotFound
            raise NotFound()
        serializer = LinkWatchSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(LinkWatchSerializer(update_watch(request.user, row, **serializer.validated_data)).data)
