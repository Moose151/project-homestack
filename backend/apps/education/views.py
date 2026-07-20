"""education views — thin wrappers over selectors/services (Coding Standards §6)."""
from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.education import selectors, services
from apps.education.serializers import (
    AcademicProfileSerializer,
    AssessmentFileSerializer,
    AssessmentNoteSerializer,
    EducationAssessmentSerializer,
    EducationClassSessionSerializer,
    EducationCourseSerializer,
    EducationEventSerializer,
    EducationInstitutionSerializer,
)
from apps.permissions.drf import HomeStackPermission

_EduPerm = HomeStackPermission.for_resource("education")


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

class EducationSearchView(APIView):
    permission_classes = [_EduPerm]

    def get(self, request: Request) -> Response:
        query = (request.query_params.get("q") or "").strip()
        if not query:
            return Response({"courses": [], "assessments": [], "class_sessions": [], "events": []})
        r = selectors.search_education(request.user, query)
        return Response({
            "courses": EducationCourseSerializer(r["courses"], many=True).data,
            "assessments": EducationAssessmentSerializer(r["assessments"], many=True).data,
            "class_sessions": EducationClassSessionSerializer(r["class_sessions"], many=True).data,
            "events": EducationEventSerializer(r["events"], many=True).data,
        })


# ---------------------------------------------------------------------------
# Institutions
# ---------------------------------------------------------------------------

class InstitutionListView(APIView):
    permission_classes = [_EduPerm]

    def get(self, request: Request) -> Response:
        return Response(EducationInstitutionSerializer(
            selectors.list_institutions(request.user), many=True).data)

    def post(self, request: Request) -> Response:
        serializer = EducationInstitutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_institution(request.user, **serializer.validated_data)
        return Response(EducationInstitutionSerializer(obj).data, status=status.HTTP_201_CREATED)


class InstitutionDetailView(APIView):
    permission_classes = [_EduPerm]

    def _get(self, pk: int):
        obj = selectors.get_institution(pk)
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request: Request, institution_id: int) -> Response:
        return Response(EducationInstitutionSerializer(self._get(institution_id)).data)

    def patch(self, request: Request, institution_id: int) -> Response:
        obj = self._get(institution_id)
        serializer = EducationInstitutionSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_institution(request.user, obj, **serializer.validated_data)
        return Response(EducationInstitutionSerializer(obj).data)

    def delete(self, request: Request, institution_id: int) -> Response:
        services.delete_institution(request.user, self._get(institution_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Courses
# ---------------------------------------------------------------------------

class CourseListView(APIView):
    permission_classes = [_EduPerm]

    def get(self, request: Request) -> Response:
        include_archived = request.query_params.get("archived") == "1"
        courses = selectors.list_courses(
            request.user, include_archived=include_archived, student_id=_int_param(request, "person"),
        )
        return Response(EducationCourseSerializer(courses, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = EducationCourseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_course(request.user, **serializer.validated_data)
        return Response(EducationCourseSerializer(obj).data, status=status.HTTP_201_CREATED)


class CourseDetailView(APIView):
    permission_classes = [_EduPerm]

    def _get(self, pk: int):
        obj = selectors.get_course(pk)
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request: Request, course_id: int) -> Response:
        return Response(EducationCourseSerializer(self._get(course_id)).data)

    def patch(self, request: Request, course_id: int) -> Response:
        obj = self._get(course_id)
        serializer = EducationCourseSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_course(request.user, obj, **serializer.validated_data)
        return Response(EducationCourseSerializer(obj).data)

    def delete(self, request: Request, course_id: int) -> Response:
        services.delete_course(request.user, self._get(course_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Assessments
# ---------------------------------------------------------------------------

class AssessmentListView(APIView):
    permission_classes = [_EduPerm]

    def get(self, request: Request) -> Response:
        assessments = selectors.list_assessments(
            request.user,
            upcoming_only=request.query_params.get("upcoming") == "1",
            open_only=request.query_params.get("open") == "1",
            course_id=_int_param(request, "course"),
            person_id=_int_param(request, "person"),
        )
        return Response(EducationAssessmentSerializer(assessments, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = EducationAssessmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_assessment(request.user, **serializer.validated_data)
        return Response(EducationAssessmentSerializer(obj).data, status=status.HTTP_201_CREATED)


class AssessmentDetailView(APIView):
    permission_classes = [_EduPerm]

    def _get(self, pk: int):
        obj = selectors.get_assessment(pk)
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request: Request, assessment_id: int) -> Response:
        return Response(EducationAssessmentSerializer(self._get(assessment_id)).data)

    def patch(self, request: Request, assessment_id: int) -> Response:
        obj = self._get(assessment_id)
        serializer = EducationAssessmentSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_assessment(request.user, obj, **serializer.validated_data)
        return Response(EducationAssessmentSerializer(obj).data)

    def delete(self, request: Request, assessment_id: int) -> Response:
        services.delete_assessment(request.user, self._get(assessment_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Assessment notes
# ---------------------------------------------------------------------------

class AssessmentNoteListView(APIView):
    permission_classes = [_EduPerm]

    def _get_assessment(self, pk: int):
        obj = selectors.get_assessment(pk)
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request: Request, assessment_id: int) -> Response:
        assessment = self._get_assessment(assessment_id)
        return Response(AssessmentNoteSerializer(
            selectors.list_assessment_notes(assessment), many=True).data)

    def post(self, request: Request, assessment_id: int) -> Response:
        assessment = self._get_assessment(assessment_id)
        serializer = AssessmentNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = services.create_assessment_note(
            request.user, assessment, serializer.validated_data["body"]
        )
        return Response(AssessmentNoteSerializer(note).data, status=status.HTTP_201_CREATED)


class AssessmentNoteDetailView(APIView):
    permission_classes = [_EduPerm]
    permission_action = "edit"  # note create/edit/delete all fall under education.edit

    def _get(self, pk: int):
        obj = selectors.get_assessment_note(pk)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, assessment_id: int, note_id: int) -> Response:
        note = self._get(note_id)
        serializer = AssessmentNoteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        note = services.update_assessment_note(
            request.user, note, serializer.validated_data.get("body", note.body)
        )
        return Response(AssessmentNoteSerializer(note).data)

    def delete(self, request: Request, assessment_id: int, note_id: int) -> Response:
        services.delete_assessment_note(request.user, self._get(note_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Assessment files
# ---------------------------------------------------------------------------

class AssessmentFileListView(APIView):
    permission_classes = [_EduPerm]

    def _get_assessment(self, pk: int):
        obj = selectors.get_assessment(pk)
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request: Request, assessment_id: int) -> Response:
        assessment = self._get_assessment(assessment_id)
        return Response(AssessmentFileSerializer(
            selectors.list_assessment_files(assessment), many=True,
            context={"request": request}).data)

    def post(self, request: Request, assessment_id: int) -> Response:
        assessment = self._get_assessment(assessment_id)
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response({"file": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)
        label = (request.data.get("label") or "").strip()
        obj = services.create_assessment_file(request.user, assessment, uploaded_file, label=label)
        return Response(
            AssessmentFileSerializer(obj, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class AssessmentFileDetailView(APIView):
    permission_classes = [_EduPerm]
    permission_action = "edit"  # file upload/delete falls under education.edit

    def _get(self, pk: int):
        obj = selectors.get_assessment_file(pk)
        if obj is None:
            raise NotFound()
        return obj

    def delete(self, request: Request, assessment_id: int, file_id: int) -> Response:
        services.delete_assessment_file(request.user, self._get(file_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Class sessions (timetable)
# ---------------------------------------------------------------------------

class ClassSessionListView(APIView):
    permission_classes = [_EduPerm]

    def get(self, request: Request) -> Response:
        sessions = selectors.list_class_sessions(
            request.user,
            course_id=_int_param(request, "course"),
            student_id=_int_param(request, "person"),
        )
        return Response(EducationClassSessionSerializer(sessions, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = EducationClassSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_class_session(request.user, **serializer.validated_data)
        return Response(EducationClassSessionSerializer(obj).data, status=status.HTTP_201_CREATED)


class ClassSessionDetailView(APIView):
    permission_classes = [_EduPerm]

    def _get(self, pk: int):
        obj = selectors.get_class_session(pk)
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request: Request, session_id: int) -> Response:
        return Response(EducationClassSessionSerializer(self._get(session_id)).data)

    def patch(self, request: Request, session_id: int) -> Response:
        obj = self._get(session_id)
        serializer = EducationClassSessionSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_class_session(request.user, obj, **serializer.validated_data)
        return Response(EducationClassSessionSerializer(obj).data)

    def delete(self, request: Request, session_id: int) -> Response:
        services.delete_class_session(request.user, self._get(session_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Education events
# ---------------------------------------------------------------------------

class EventListView(APIView):
    permission_classes = [_EduPerm]

    def get(self, request: Request) -> Response:
        events = selectors.list_events(
            request.user,
            upcoming_only=request.query_params.get("upcoming") == "1",
            course_id=_int_param(request, "course"),
            person_id=_int_param(request, "person"),
        )
        return Response(EducationEventSerializer(events, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = EducationEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = services.create_event(request.user, **serializer.validated_data)
        return Response(EducationEventSerializer(obj).data, status=status.HTTP_201_CREATED)


class EventDetailView(APIView):
    permission_classes = [_EduPerm]

    def _get(self, pk: int):
        obj = selectors.get_event(pk)
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request: Request, event_id: int) -> Response:
        return Response(EducationEventSerializer(self._get(event_id)).data)

    def patch(self, request: Request, event_id: int) -> Response:
        obj = self._get(event_id)
        serializer = EducationEventSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = services.update_event(request.user, obj, **serializer.validated_data)
        return Response(EducationEventSerializer(obj).data)

    def delete(self, request: Request, event_id: int) -> Response:
        services.delete_event(request.user, self._get(event_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Academic profile (per-person)
# ---------------------------------------------------------------------------

class AcademicProfileView(APIView):
    """GET/PATCH the academic profile for a given person.

    GET creates a blank profile on first access (idempotent). PATCH updates it.
    Also returns date-bucketed courses (current/upcoming/past) for the profile page.
    """
    permission_classes = [_EduPerm]

    def get(self, request: Request, person_id: int) -> Response:
        profile = services.get_or_create_academic_profile(request.user, person_id)
        course_buckets = selectors.list_courses_for_profile(person_id, user=request.user)
        return Response({
            "profile": AcademicProfileSerializer(profile).data,
            "courses": {
                bucket: EducationCourseSerializer(courses, many=True).data
                for bucket, courses in course_buckets.items()
            },
        })

    def patch(self, request: Request, person_id: int) -> Response:
        profile = services.get_or_create_academic_profile(request.user, person_id)
        serializer = AcademicProfileSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        # Only pass recognised profile fields (exclude person_id, read-only fields)
        profile_data = {
            k: v for k, v in serializer.validated_data.items()
            if k not in {"person_id", "current_credits"}
        }
        profile = services.update_academic_profile(request.user, profile, **profile_data)
        return Response(AcademicProfileSerializer(profile).data)
