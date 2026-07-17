from django.urls import path

from apps.education.views import (
    AcademicProfileView,
    AssessmentDetailView,
    AssessmentFileDetailView,
    AssessmentFileListView,
    AssessmentListView,
    AssessmentNoteDetailView,
    AssessmentNoteListView,
    ClassSessionDetailView,
    ClassSessionListView,
    CourseDetailView,
    CourseListView,
    EducationSearchView,
    InstitutionDetailView,
    InstitutionListView,
)

urlpatterns = [
    path("search/", EducationSearchView.as_view(), name="education-search"),

    path("institutions/", InstitutionListView.as_view(), name="education-institution-list"),
    path("institutions/<int:institution_id>/", InstitutionDetailView.as_view(), name="education-institution-detail"),

    path("courses/", CourseListView.as_view(), name="education-course-list"),
    path("courses/<int:course_id>/", CourseDetailView.as_view(), name="education-course-detail"),

    path("assessments/", AssessmentListView.as_view(), name="education-assessment-list"),
    path("assessments/<int:assessment_id>/", AssessmentDetailView.as_view(), name="education-assessment-detail"),
    path("assessments/<int:assessment_id>/notes/", AssessmentNoteListView.as_view(), name="education-assessment-note-list"),
    path("assessments/<int:assessment_id>/notes/<int:note_id>/", AssessmentNoteDetailView.as_view(), name="education-assessment-note-detail"),
    path("assessments/<int:assessment_id>/files/", AssessmentFileListView.as_view(), name="education-assessment-file-list"),
    path("assessments/<int:assessment_id>/files/<int:file_id>/", AssessmentFileDetailView.as_view(), name="education-assessment-file-detail"),

    path("classes/", ClassSessionListView.as_view(), name="education-class-list"),
    path("classes/<int:session_id>/", ClassSessionDetailView.as_view(), name="education-class-detail"),

    path("profile/<int:person_id>/", AcademicProfileView.as_view(), name="education-academic-profile"),
]
