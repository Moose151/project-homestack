"""pets views — thin wrappers over selectors/services (Coding Standards §6)."""
from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.pets import selectors, services
from apps.pets.serializers import (
    PetAppointmentSerializer,
    PetSerializer,
    PetTreatmentSerializer,
)
from apps.permissions.drf import HomeStackPermission

_PetPerm = HomeStackPermission.for_resource("pets")


def _int_param(request: Request, name: str) -> int | None:
    raw = request.query_params.get(name)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class PetSearchView(APIView):
    permission_classes = [_PetPerm]

    def get(self, request: Request) -> Response:
        query = (request.query_params.get("q") or "").strip()
        if not query:
            return Response({"pets": [], "treatments": [], "appointments": []})
        r = selectors.search_pets(request.user, query)
        return Response({
            "pets": PetSerializer(r["pets"], many=True).data,
            "treatments": PetTreatmentSerializer(r["treatments"], many=True).data,
            "appointments": PetAppointmentSerializer(r["appointments"], many=True).data,
        })


# ---------------------------------------------------------------------------
# Pets
# ---------------------------------------------------------------------------

class PetListView(APIView):
    permission_classes = [_PetPerm]

    def get(self, request: Request) -> Response:
        pets = selectors.list_pets(
            request.user, include_archived=request.query_params.get("archived") == "1"
        )
        return Response(PetSerializer(pets, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = PetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_pet(request.user, **serializer.validated_data)
        return Response(PetSerializer(obj).data, status=status.HTTP_201_CREATED)


class PetDetailView(APIView):
    permission_classes = [_PetPerm]

    def _get(self, pk: int):
        obj = selectors.get_pet(pk)
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request: Request, pet_id: int) -> Response:
        return Response(PetSerializer(self._get(pet_id)).data)

    def patch(self, request: Request, pet_id: int) -> Response:
        obj = self._get(pet_id)
        serializer = PetSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_pet(request.user, obj, **serializer.validated_data)
        return Response(PetSerializer(obj).data)

    def delete(self, request: Request, pet_id: int) -> Response:
        services.delete_pet(request.user, self._get(pet_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Treatments
# ---------------------------------------------------------------------------

class TreatmentListView(APIView):
    permission_classes = [_PetPerm]

    def get(self, request: Request) -> Response:
        treatments = selectors.list_treatments(
            request.user,
            pet_id=_int_param(request, "pet"),
            due_only=request.query_params.get("due") == "1",
        )
        return Response(PetTreatmentSerializer(treatments, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = PetTreatmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_treatment(request.user, **serializer.validated_data)
        return Response(PetTreatmentSerializer(obj).data, status=status.HTTP_201_CREATED)


class TreatmentDetailView(APIView):
    permission_classes = [_PetPerm]

    def _get(self, pk: int):
        obj = selectors.get_treatment(pk)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, treatment_id: int) -> Response:
        obj = self._get(treatment_id)
        serializer = PetTreatmentSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_treatment(request.user, obj, **serializer.validated_data)
        return Response(PetTreatmentSerializer(obj).data)

    def delete(self, request: Request, treatment_id: int) -> Response:
        services.delete_treatment(request.user, self._get(treatment_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class TreatmentCompleteView(APIView):
    """Mark a treatment done — stamps last_done_at and advances next_due_at (RRULE)."""
    permission_classes = [_PetPerm]
    permission_action = "edit"

    def post(self, request: Request, treatment_id: int) -> Response:
        obj = selectors.get_treatment(treatment_id)
        if obj is None:
            raise NotFound()
        obj = services.complete_treatment(request.user, obj)
        return Response(PetTreatmentSerializer(obj).data)


# ---------------------------------------------------------------------------
# Appointments
# ---------------------------------------------------------------------------

class AppointmentListView(APIView):
    permission_classes = [_PetPerm]

    def get(self, request: Request) -> Response:
        appointments = selectors.list_appointments(
            request.user,
            pet_id=_int_param(request, "pet"),
            upcoming_only=request.query_params.get("upcoming") == "1",
        )
        return Response(PetAppointmentSerializer(appointments, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = PetAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_appointment(request.user, **serializer.validated_data)
        return Response(PetAppointmentSerializer(obj).data, status=status.HTTP_201_CREATED)


class AppointmentDetailView(APIView):
    permission_classes = [_PetPerm]

    def _get(self, pk: int):
        obj = selectors.get_appointment(pk)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, appointment_id: int) -> Response:
        obj = self._get(appointment_id)
        serializer = PetAppointmentSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_appointment(request.user, obj, **serializer.validated_data)
        return Response(PetAppointmentSerializer(obj).data)

    def delete(self, request: Request, appointment_id: int) -> Response:
        services.delete_appointment(request.user, self._get(appointment_id))
        return Response(status=status.HTTP_204_NO_CONTENT)
