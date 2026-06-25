"""achievements views — thin read endpoints (Coding Standards §6).

Badges are read-only over the API; they are *awarded* by the event handlers, never via HTTP.
"""
from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.achievements import selectors
from apps.achievements.serializers import BadgeSerializer, PersonBadgeSerializer
from apps.permissions.drf import HomeStackPermission

_Perm = HomeStackPermission.for_resource("achievements")


class BadgeListView(APIView):
    """The full badge catalogue (what can be earned)."""

    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        return Response(BadgeSerializer(selectors.all_badges(), many=True).data)


class PersonBadgesView(APIView):
    """Badges a person has earned. ?person_id= for a specific person, else the caller's own."""

    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        person_id = request.query_params.get("person_id")
        if not person_id:
            person = getattr(request.user, "person_profile", None)
            person_id = person.id if person else None
        if not person_id:
            return Response([])
        return Response(PersonBadgeSerializer(selectors.person_badges(int(person_id)), many=True).data)
