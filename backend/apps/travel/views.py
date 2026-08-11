from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.permissions.drf import HomeStackPermission
from apps.travel import selectors, services
from apps.travel.serializers import BookingSerializer, TravelIdeaSerializer, TripSerializer

_Perm = HomeStackPermission.for_resource("travel")


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except services.TravelError as exc:
        raise ValidationError({"detail": str(exc)}) from exc


class TripListView(APIView):
    permission_classes = [_Perm]

    def get(self, request):
        return Response(TripSerializer(selectors.list_trips(request.user), many=True).data)

    def post(self, request):
        serializer = TripSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_trip(request.user, **serializer.validated_data)
        return Response(TripSerializer(selectors.get_trip(request.user, obj.id)).data, status=status.HTTP_201_CREATED)


class TripDetailView(APIView):
    permission_classes = [_Perm]

    def _get(self, request, pk):
        obj = selectors.get_trip(request.user, pk)
        if not obj:
            raise NotFound()
        return obj

    def get(self, request, trip_id):
        return Response(TripSerializer(self._get(request, trip_id)).data)

    def patch(self, request, trip_id):
        serializer = TripSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_trip(request.user, self._get(request, trip_id), **serializer.validated_data)
        return Response(TripSerializer(selectors.get_trip(request.user, obj.id)).data)

    def delete(self, request, trip_id):
        services.delete_trip(request.user, self._get(request, trip_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class IdeaListView(APIView):
    permission_classes = [_Perm]

    def get(self, request):
        return Response(TravelIdeaSerializer(selectors.list_ideas(request.user), many=True).data)

    def post(self, request):
        serializer = TravelIdeaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_idea(request.user, **serializer.validated_data)
        return Response(TravelIdeaSerializer(selectors.get_idea(request.user, obj.id)).data, status=status.HTTP_201_CREATED)


class IdeaDetailView(APIView):
    permission_classes = [_Perm]

    def _get(self, request, pk):
        obj = selectors.get_idea(request.user, pk)
        if not obj:
            raise NotFound()
        return obj

    def patch(self, request, idea_id):
        serializer = TravelIdeaSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_idea(request.user, self._get(request, idea_id), **serializer.validated_data)
        return Response(TravelIdeaSerializer(selectors.get_idea(request.user, obj.id)).data)

    def delete(self, request, idea_id):
        services.delete_idea(request.user, self._get(request, idea_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class IdeaConvertView(APIView):
    permission_classes = [_Perm]
    permission_action = "edit"

    def post(self, request, idea_id):
        idea = selectors.get_idea(request.user, idea_id)
        if not idea:
            raise NotFound()
        trip = services.convert_idea(request.user, idea)
        return Response(TripSerializer(selectors.get_trip(request.user, trip.id)).data)


class BookingListView(APIView):
    permission_classes = [_Perm]

    def post(self, request, trip_id):
        trip = selectors.get_trip(request.user, trip_id)
        if not trip:
            raise NotFound()
        serializer = BookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_booking(request.user, trip, **serializer.validated_data)
        return Response(BookingSerializer(obj).data, status=status.HTTP_201_CREATED)


class BookingDetailView(APIView):
    permission_classes = [_Perm]

    def _get(self, request, pk):
        obj = selectors.get_booking(request.user, pk)
        if not obj:
            raise NotFound()
        return obj

    def patch(self, request, booking_id):
        serializer = BookingSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(BookingSerializer(services.update_booking(request.user, self._get(request, booking_id), **serializer.validated_data)).data)

    def delete(self, request, booking_id):
        services.delete_booking(request.user, self._get(request, booking_id))
        return Response(status=status.HTTP_204_NO_CONTENT)
