"""people URL config — CRUD endpoints at /api/v1/people/."""
from django.urls import path

from apps.people import views

urlpatterns = [
    path("", views.PersonListView.as_view(), name="people-list"),
    path("<int:person_id>/", views.PersonDetailView.as_view(), name="people-detail"),
]
