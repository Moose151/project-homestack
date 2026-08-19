from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.fitness import selectors, services
from apps.fitness.models import SessionExercise, SessionSet
from apps.fitness.serializers import (
    AddSessionExerciseSerializer, ExerciseSerializer, PersonalRecordSerializer,
    SessionExerciseSerializer, SessionSetSerializer, LogRunSerializer,
    StartSessionSerializer,
    TrainingProgramReadSerializer, TrainingProgramWriteSerializer, WorkoutSessionSerializer,
)
from apps.permissions.drf import HomeStackPermission

_Perm = HomeStackPermission.for_resource("fitness")


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except services.FitnessError as exc:
        raise ValidationError({"detail": str(exc)}) from exc


def _integer(request, key):
    raw = request.query_params.get(key)
    try:
        return int(raw) if raw else None
    except ValueError:
        raise ValidationError({key: "Enter a valid number."})


class ExerciseListView(APIView):
    permission_classes = [_Perm]

    def get(self, request):
        rows = selectors.list_exercises(
            request.user, query=request.query_params.get("q", ""),
            exercise_type=request.query_params.get("type", ""),
            muscle_group=request.query_params.get("muscle_group", ""),
            include_archived=request.query_params.get("archived") == "1",
        )
        return Response(ExerciseSerializer(rows, many=True).data)

    def post(self, request):
        serializer = ExerciseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_exercise(request.user, **serializer.validated_data)
        return Response(ExerciseSerializer(obj).data, status=status.HTTP_201_CREATED)


class ExerciseDetailView(APIView):
    permission_classes = [_Perm]

    def _get(self, pk):
        obj = selectors.get_exercise(pk)
        if not obj:
            raise NotFound()
        return obj

    def patch(self, request, exercise_id):
        serializer = ExerciseSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_exercise(request.user, self._get(exercise_id), **serializer.validated_data)
        return Response(ExerciseSerializer(obj).data)

    def delete(self, request, exercise_id):
        services.delete_exercise(request.user, self._get(exercise_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProgramListView(APIView):
    permission_classes = [_Perm]

    def get(self, request):
        rows = selectors.list_programs(request.user, assigned_person_id=_integer(request, "person"), include_archived=request.query_params.get("archived") == "1")
        return Response(TrainingProgramReadSerializer(rows, many=True).data)

    def post(self, request):
        serializer = TrainingProgramWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = _run(services.create_program, request.user, **serializer.validated_data)
        obj = selectors.get_program(request.user, obj.id)
        return Response(TrainingProgramReadSerializer(obj).data, status=status.HTTP_201_CREATED)


class ProgramDetailView(APIView):
    permission_classes = [_Perm]

    def _get(self, user, pk):
        obj = selectors.get_program(user, pk)
        if not obj:
            raise NotFound()
        return obj

    def get(self, request, program_id):
        return Response(TrainingProgramReadSerializer(self._get(request.user, program_id)).data)

    def patch(self, request, program_id):
        serializer = TrainingProgramWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = _run(services.update_program, request.user, self._get(request.user, program_id), **serializer.validated_data)
        return Response(TrainingProgramReadSerializer(selectors.get_program(request.user, obj.id)).data)

    def delete(self, request, program_id):
        _run(services.delete_program, request.user, self._get(request.user, program_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionListView(APIView):
    permission_classes = [_Perm]

    def get(self, request):
        rows = selectors.list_sessions(request.user, person_id=_integer(request, "person"), status=request.query_params.get("status", ""))
        return Response(WorkoutSessionSerializer(rows, many=True).data)


class SessionStartView(APIView):
    permission_classes = [_Perm]

    def post(self, request):
        serializer = StartSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = _run(services.start_session, request.user, **serializer.validated_data)
        return Response(WorkoutSessionSerializer(selectors.get_session(request.user, obj.id)).data, status=status.HTTP_201_CREATED)


class SessionLogRunView(APIView):
    """Record a completed run in one request.

    Deliberately its own endpoint rather than start -> add exercise -> add set -> finish: the
    point of the feature is that logging an ordinary run is one step. It still lands as a normal
    completed session through the shared services, so nothing about history, records or
    permissions is special-cased.
    """

    permission_classes = [_Perm]

    def post(self, request):
        serializer = LogRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = _run(services.log_run, request.user, **serializer.validated_data)
        return Response(
            WorkoutSessionSerializer(selectors.get_session(request.user, obj.id)).data,
            status=status.HTTP_201_CREATED,
        )


class SessionDetailView(APIView):
    permission_classes = [_Perm]

    def get(self, request, session_id):
        obj = selectors.get_session(request.user, session_id)
        if not obj:
            raise NotFound()
        return Response(WorkoutSessionSerializer(obj).data)


class SessionAddExerciseView(APIView):
    permission_classes = [_Perm]
    permission_action = "edit"

    def post(self, request, session_id):
        session = selectors.get_session(request.user, session_id)
        if not session:
            raise NotFound()
        serializer = AddSessionExerciseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = _run(services.add_session_exercise, request.user, session, **serializer.validated_data)
        return Response(SessionExerciseSerializer(obj).data, status=status.HTTP_201_CREATED)


class SessionExerciseDropView(APIView):
    permission_classes = [_Perm]
    permission_action = "edit"

    def post(self, request, entry_id):
        obj = SessionExercise.objects.select_related("session").filter(pk=entry_id).first()
        if not obj or not selectors.get_session(request.user, obj.session_id):
            raise NotFound()
        return Response(SessionExerciseSerializer(_run(services.drop_session_exercise, request.user, obj)).data)


class SessionExerciseAddSetView(APIView):
    permission_classes = [_Perm]
    permission_action = "edit"

    def post(self, request, entry_id):
        obj = SessionExercise.objects.select_related("session").filter(pk=entry_id).first()
        if not obj or not selectors.get_session(request.user, obj.session_id):
            raise NotFound()
        return Response(SessionSetSerializer(_run(services.add_set, request.user, obj)).data, status=status.HTTP_201_CREATED)


class SessionSetDetailView(APIView):
    permission_classes = [_Perm]

    def patch(self, request, set_id):
        obj = SessionSet.objects.select_related("session_exercise__session").filter(pk=set_id).first()
        if not obj or not selectors.get_session(request.user, obj.session_exercise.session_id):
            raise NotFound()
        serializer = SessionSetSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = _run(services.update_set, request.user, obj, **serializer.validated_data)
        return Response(SessionSetSerializer(obj).data)


class SessionFinishView(APIView):
    permission_classes = [_Perm]
    permission_action = "edit"

    def post(self, request, session_id):
        obj = selectors.get_session(request.user, session_id)
        if not obj:
            raise NotFound()
        obj = _run(services.finish_session, request.user, obj, notes=request.data.get("notes"))
        return Response(WorkoutSessionSerializer(selectors.get_session(request.user, obj.id)).data)


class SessionAbandonView(APIView):
    permission_classes = [_Perm]
    permission_action = "edit"

    def post(self, request, session_id):
        obj = selectors.get_session(request.user, session_id)
        if not obj:
            raise NotFound()
        obj = _run(services.abandon_session, request.user, obj)
        return Response(WorkoutSessionSerializer(obj).data)


class RecordListView(APIView):
    permission_classes = [_Perm]

    def get(self, request):
        rows = selectors.list_records(request.user, person_id=_integer(request, "person"), exercise_id=_integer(request, "exercise"))
        return Response(PersonalRecordSerializer(rows, many=True).data)
