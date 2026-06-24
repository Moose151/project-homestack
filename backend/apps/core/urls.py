"""core URL config — household endpoint."""
from django.urls import path

from apps.core import views

urlpatterns = [
    path("", views.HouseholdView.as_view(), name="household"),
]
