from django.urls import path

from apps.pets.views import (
    AppointmentDetailView,
    AppointmentListView,
    PetDetailView,
    PetListView,
    PetSearchView,
    TreatmentCompleteView,
    TreatmentDetailView,
    TreatmentListView,
)

urlpatterns = [
    path("search/", PetSearchView.as_view(), name="pets-search"),

    path("pets/", PetListView.as_view(), name="pets-pet-list"),
    path("pets/<int:pet_id>/", PetDetailView.as_view(), name="pets-pet-detail"),

    path("treatments/", TreatmentListView.as_view(), name="pets-treatment-list"),
    path("treatments/<int:treatment_id>/", TreatmentDetailView.as_view(), name="pets-treatment-detail"),
    path("treatments/<int:treatment_id>/complete/", TreatmentCompleteView.as_view(), name="pets-treatment-complete"),

    path("appointments/", AppointmentListView.as_view(), name="pets-appointment-list"),
    path("appointments/<int:appointment_id>/", AppointmentDetailView.as_view(), name="pets-appointment-detail"),
]
