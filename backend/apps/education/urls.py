from django.urls import path

from apps.education.views import (
    AssessmentDetailView,
    AssessmentListView,
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

    path("classes/", ClassSessionListView.as_view(), name="education-class-list"),
    path("classes/<int:session_id>/", ClassSessionDetailView.as_view(), name="education-class-detail"),
]
