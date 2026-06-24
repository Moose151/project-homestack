"""
people views — thin wrappers that validate input and delegate to services/selectors (D10).

Endpoints (API spec §3):
  GET    /api/v1/people/
  POST   /api/v1/people/
  GET    /api/v1/people/{person_id}/
  PATCH  /api/v1/people/{person_id}/
  DELETE /api/v1/people/{person_id}/

Permissions: enforced via HomeStackPermission (D10). No ad-hoc checks in views.
"""
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.people import selectors, services
from apps.people.serializers import PersonSerializer, PersonWriteSerializer
from apps.permissions.drf import HomeStackPermission

_PeoplePermission = HomeStackPermission.for_resource("people")


class PersonListView(APIView):
    permission_classes = [_PeoplePermission]

    def get(self, request: Request) -> Response:
        people = selectors.list_people(user=request.user)
        return Response(PersonSerializer(people, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = PersonWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        person = services.create_person(request.user, **serializer.validated_data)
        return Response(PersonSerializer(person).data, status=status.HTTP_201_CREATED)


class PersonDetailView(APIView):
    permission_classes = [_PeoplePermission]

    def _get_person_or_404(self, person_id: int) -> Response | None:
        person = selectors.get_person_by_id(person_id)
        if person is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return person

    def get(self, request: Request, person_id: int) -> Response:
        result = self._get_person_or_404(person_id)
        if isinstance(result, Response):
            return result
        return Response(PersonSerializer(result).data)

    def patch(self, request: Request, person_id: int) -> Response:
        result = self._get_person_or_404(person_id)
        if isinstance(result, Response):
            return result
        serializer = PersonWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        person = services.update_person(request.user, result, **serializer.validated_data)
        return Response(PersonSerializer(person).data)

    def delete(self, request: Request, person_id: int) -> Response:
        result = self._get_person_or_404(person_id)
        if isinstance(result, Response):
            return result
        services.delete_person(request.user, result)
        return Response(status=status.HTTP_204_NO_CONTENT)
