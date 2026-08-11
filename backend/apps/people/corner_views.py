from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.people import corner_services, corners, selectors
from apps.permissions.drf import HomeStackPermission


class CornerDetailView(APIView):
    permission_classes = [HomeStackPermission.for_resource("corners")]

    def get(self, request: Request, person_id: int) -> Response:
        person = selectors.get_person_by_id(person_id)
        if person is None:
            raise NotFound()
        try:
            days = int(request.query_params.get("days", "30"))
        except ValueError:
            days = 30
        return Response(corners.build_corner(request.user, person, days=days))


class CornerReactionView(APIView):
    permission_classes = [HomeStackPermission.for_resource("corners")]
    permission_action = "react"

    def post(self, request: Request, person_id: int) -> Response:
        person = selectors.get_person_by_id(person_id)
        if person is None:
            raise NotFound()
        activity_key = str(request.data.get("activity_key") or "")
        emoji = str(request.data.get("emoji") or "")
        if not activity_key:
            raise ValidationError({"activity_key": "This field is required."})
        try:
            active = corner_services.toggle_reaction(
                acting_user=request.user, owner=person, activity_key=activity_key, emoji=emoji
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response({"active": active, "corner": corners.build_corner(request.user, person)})
